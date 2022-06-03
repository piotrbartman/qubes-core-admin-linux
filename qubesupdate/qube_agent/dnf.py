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

import logging
import shutil
from typing import List, Tuple

from package_manager import PackageManager
from utils import run_cmd

log = logging.getLogger(__name__)


class DNF(PackageManager):
    def __init__(self):
        super().__init__()
        pck_mng_path = shutil.which('dnf')
        if pck_mng_path is not None:
            pck_mngr = 'dnf'
        else:
            pck_mng_path = shutil.which('yum')
            if pck_mng_path is not None:
                pck_mngr = 'yum'
            else:
                raise RuntimeError("Package manager not found!")
        self.package_manager: str = pck_mngr

    def refresh(self) -> Tuple[int, str, str]:
        """
        Use package manager to refresh available packages.

        :return: (return_code, stdout, stderr)
        """
        out = ""
        err = ""

        cmd = [self.package_manager,
               "-q",
               "-y",
               "clean",
               "expire-cache"]
        ret_code, stdout, stderr = run_cmd(cmd, self.log)
        return_code = ret_code
        out += stdout
        err += stderr

        cmd = [self.package_manager,
               "-q",
               "-y",
               "check-update"]
        ret_code, stdout, stderr = run_cmd(cmd, self.log)
        return_code = max(ret_code, return_code)
        out += stdout
        err += stderr

        return return_code, out, err

    def get_packages(self):
        """
        Use rpm to return the installed packages and their versions.
        """

        cmd = [
            "rpm",
            "-qa",
            "--queryformat",
            "%{NAME} %{VERSION}%{RELEASE}\n",
        ]
        # EXAMPLE OUTPUT:
        # qubes-core-agent 4.1.351.fc34
        ret_code, stdout, stderr = run_cmd(cmd, self.log)

        packages = {}
        for line in stdout.splitlines():
            cols = line.split()
            package, version = cols
            packages.setdefault(package, []).append(version)

        return packages

    def parse_options(self, *args, **kwargs) -> List[str]:
        """
        Parse extra options for package manager.
        """
        raise NotImplementedError()  # TODO

    def get_action(self, remove_obsolete) -> List[str]:
        """
        Disable or enforce obsolete flag in dnf/yum.
        """
        if remove_obsolete:
            return ["--obsoletes", "upgrade"]
        else:
            return ["--setopt=obsoletes=0",
                    "upgrade" if self.package_manager == "dnf" else "update"]
