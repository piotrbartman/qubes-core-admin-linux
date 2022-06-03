# coding=utf-8
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2022  Piotr Bartman <prbartman@invisiblethingslab.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.

import os
import logging
import sys
from typing import Optional, Dict, List, Tuple

from utils import compare_packages, run_cmd

FORMAT_LOG = '%(message)s'
LOGPATH = '/tmp/qubesupdate'  # TODO
formatter_log = logging.Formatter(FORMAT_LOG)


class PackageManager:
    def __init__(self, loglevel="NOTSET"):
        self.package_manager: Optional[str] = None
        self.log = logging.getLogger('qubesupdate.agent.PackageManager')
        self.log.setLevel(loglevel)
        self.log_path = os.path.join(LOGPATH, 'update-agent.log')
        handler_log = logging.FileHandler(self.log_path, encoding='utf-8')
        handler_log.setFormatter(formatter_log)
        self.log.addHandler(handler_log)
        self.log.propagate = False

    def upgrade(
            self,
            refresh: bool = True,
            enforce_refresh: bool = True,
            remove_obsolete: bool = False,
            *args
    ):
        """
        Upgrade packages using system package manager.

        :param refresh: refresh available packages first
        :param enforce_refresh: if `refresh`, and refresh fails, stop and fail
        :param remove_obsolete: remove obsolete packages
        :return: return code
        """
        return_code = 0

        if refresh:
            return_code, stdout, stderr = self.refresh()
            if return_code != 0 and enforce_refresh:
                print(stdout)
                print(stderr, file=sys.stderr)
                return 1

        old_pkg = self.get_packages()

        options = []  # TODO self.parse_options(*args)

        cmd = ["sudo",
               self.package_manager,
               "-q",
               "-y",
               *options,
               *self.get_action(remove_obsolete)]

        ret_code, stdout, stderr = run_cmd(cmd, self.log)  # TODO sync progress
        return_code = max(return_code, ret_code)

        new_pkg = self.get_packages()

        changes = compare_packages(old=old_pkg, new=new_pkg)

        self.log.info("Installed packages:")
        for pkg in changes["installed"]:
            self.log.info("%s %s", pkg, changes["installed"][pkg])
        self.log.info("Updated packages:")
        for pkg in changes["updated"]:
            self.log.info("%s %s->%s",
                          pkg,
                          changes["updated"][pkg]["old"],
                          changes["updated"][pkg]["new"]
                          )
        self.log.info("Removed packages:")
        for pkg in changes["removed"]:
            self.log.info("%s %s", pkg, changes["removed"][pkg])

        return return_code

    def refresh(self) -> Tuple[int, str, str]:
        """
        Refresh available packages for upgrade.

        :return: (return_code, stdout, stderr)
        """
        raise NotImplementedError()

    def get_packages(self) -> Dict[str, List[str]]:
        """
        Return the installed packages and their versions.
        """
        raise NotImplementedError()

    def parse_options(self, *args, **kwargs) -> List[str]:
        """
        Parse extra options for package manager.
        """
        raise NotImplementedError()

    def get_action(self, remove_obsolete: bool) -> str:
        """
        Return command for upgrade or upgrade with removing obsolete packages.
        """
        raise NotImplementedError()
