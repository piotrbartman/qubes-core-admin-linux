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

import dnf
import shutil
from typing import Tuple, Callable, Optional

from dnf_cli import DNFCLI


class DNF(DNFCLI):
    def __init__(self, logpath, loglevel):
        super().__init__(logpath, loglevel)
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
        self.progress = DNFProgressReporter()

    def upgrade_internal(self, remove_obsolete: bool) -> Tuple[int, str, str]:
        """
        Use `dnf` package to upgrade and track progress.
        """
        try:
            with dnf.Base() as base:
                # Repositories serve as sources of information about packages.
                base.read_all_repos()
                # A sack is needed for querying.
                base.fill_sack()

                # base.upgrade_all()
                # exit_code = base._upgrade_internal(
                #     base.sack.query(), base.conf.obsoletes, None)
                exit_code = 0
                base.upgrade_all()

                base.resolve()
                trans = base.transaction
                if not trans:
                    return exit_code, "Nothing to upgrade", ""

                base.download_packages(trans.install_set)

                ret_code = sign_check(
                    base, trans.install_set, self.progress.stderr)
                exit_code = max(exit_code, ret_code)

                if exit_code == 0:
                    base.do_transaction(self.progress)
        except Exception as exc:
            stderr = self.progress.stderr + "\n" + str(exc)
            return 1, self.progress.stdout, stderr

        return exit_code, self.progress.stdout, self.progress.stderr


def sign_check(base, packages, output):
    exit_code = 0
    for package in packages:
        ret_code, message = base.package_signature_check(package)
        if ret_code != 0:
            exit_code = max(exit_code, ret_code)
            output += message
    return exit_code


class DNFProgressReporter:
    """
    Simple heuristic progress reporter.

    Implementation of `dnf.yum.rpmtrans.TransactionDisplay`
    It is assumed that each operation (fetch or install) of each package takes
    the same amount of time, regardless of its size.
    """

    def __init__(self, callback: Optional[Callable[[float], None]] = None):
        self.last_percent = 0.0
        self.stdout = ""
        self.stderr = ""
        if callback is None:
            self.callback = lambda p: print(f"{p:.2f}%", flush=True)
        else:
            self.callback = callback

    def progress(self, _package, action, ti_done, ti_total, ts_done, ts_total):
        """
        Report ongoing progress on a transaction item.

        :param _package: a package name
        :param action: the performed action id
        :param ti_done: number of processed bytes of the transaction item
        :param ti_total: total number of bytes of the transaction item
        :param ts_done: number of actions processed in the whole transaction
        :param ts_total: total number of actions in the whole transaction
        """
        fetch = 6
        install = 7
        if action != fetch and action != install:
            return
        percent = ti_done / ti_total * ts_done / ts_total * 100
        if self.last_percent + 1 <= percent:
            self.callback(percent)
            self.last_percent = round(percent)

    def scriptout(self, messages):
        """
        Write an output message to the fake stdout.
        """
        if messages:
            for msg in messages:
                self.stdout += msg + "\n"

    def error(self, message):
        """
        Write an error message to the fake stderr.
        """
        self.stderr += str(message) + "\n"

    def filelog(self, _package, _action):
        pass

    def verify_tsi_package(self, pkg, count, total):
        pass
