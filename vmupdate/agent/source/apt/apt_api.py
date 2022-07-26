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
from typing import List, Tuple, Callable, Optional

import apt
import apt.progress.base

from apt_cli import APTCLI


class APT(APTCLI):
    def __init__(self, logpath, loglevel):
        super().__init__(logpath, loglevel)
        self.package_manager: str = "apt-get"
        self.apt_cache = apt.cache.Cache()
        self.progress = APTProgressReporter()

        # to prevent a warning: `debconf: unable to initialize frontend: Dialog`
        os.environ['DEBIAN_FRONTEND'] = 'noninteractive'

    def refresh(self) -> Tuple[int, str, str]:
        """
        Use apt-get update to refresh available packages.

        :return: (exit_code, stdout, stderr)
        """
        success = self.apt_cache.update(self.progress.update_progress)
        self.apt_cache.open()
        ret_code = 0 if success else 1
        return ret_code, "", ""

    def upgrade_internal(self, remove_obsolete: bool) -> Tuple[int, str, str]:
        """
        Use `apt` package to upgrade and track progress.
        """
        try:
            self.apt_cache.upgrade(dist_upgrade=remove_obsolete)
            self.apt_cache.commit(
                self.progress.fetch_progress, self.progress.upgrade_progress)
        except Exception as exc:
            return 1, "", str(exc)

        return 0, self.progress.stdout, self.progress.stderr


class APTProgressReporter:
    """
    Simple heuristic progress reporter.

    It is assumed that updating takes 10%, fetching packages takes 45% and
    installing takes 45% of total time.
    """

    def __init__(self, callback: Optional[Callable[[float], None]] = None):
        self.last_percent = 0.0
        self.stdout = ""
        self.stderr = ""
        if callback is None:
            self.callback = lambda p: print(f"{p:.2f}%")
        else:
            self.callback = callback
        self.update_progress = APTProgressReporter.FetchProgress(
            lambda p: self.update(p, 0, 10), self.stderr)
        self.fetch_progress = APTProgressReporter.FetchProgress(
            lambda p: self.update(p, 10, 55), self.stderr)
        self.upgrade_progress = APTProgressReporter.UpgradeProgress(
            lambda p: self.update(p, 55, 100), self.stderr)

    # updating (OpProgress)

    def update(self, percent, start, stop):
        """
        Report ongoing progress.
        """
        _percent = start + percent * (stop - start) / 100
        if self.last_percent + 1 <= _percent:
            self.callback(_percent)
            self.last_percent = round(_percent)

    class FetchProgress(apt.progress.base.AcquireProgress):
        def __init__(self, callback, stderr):
            self.callback = callback
            self.stderr = stderr

        def fail(self, item):
            """
            Write an error message to the fake stderr.
            """
            self.stderr += str(item) + "\n"

        def pulse(self, _owner):
            """
            Report ongoing progress on fetching packages.

            Periodically invoked while the Acquire process is underway.
            This function returns a boolean value indicating whether the
            acquisition should be continued (True) or cancelled (False).
            """
            self.callback(self.current_bytes / self.total_bytes)
            return True

    class UpgradeProgress(apt.progress.base.InstallProgress):
        def __init__(self, callback: Callable[[float], None], stderr: str):
            apt.progress.base.InstallProgress.__init__(self)
            self.callback = callback
            self.stderr = stderr

        def status_change(self, _pkg, percent, _status):
            """
            Report ongoing progress on installing/upgrading packages.
            """
            self.callback(percent)

        def error(self, pkg, errormsg):
            """
            Write an error message to the fake stderr.
            """
            self.stderr += "Error during installation " + str(pkg) + ":" \
                           + str(errormsg) + "\n"
