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
import time
from os.path import join, isfile


class QubeConnection:
    """
    Run scripts in the qube.

    1. Initialize the state of connection.
    2. Transfer files to a new directory, start the qube if not running.
    3. Run an entrypoint script, return the output.
    4. On close, remove the created directory,
       stop the qube if it was started by this connection.
    """

    def __init__(self, qube, dest_dir, logger):
        self.qube = qube
        self.dest_dir = dest_dir
        self.logger = logger
        self._initially_running = None
        self.__connected = False

    def __enter__(self):
        self._initially_running = self.qube.is_running()
        self.__connected = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.info('Remove %s', self.dest_dir)
        exit_code, stdout_lines = self._run_shell_command_in_qube(
            self.qube, 'rm -r {}'.format(self.dest_dir))
        for line in stdout_lines:
            self.logger.debug('Remove output: %s', line)
        self.logger.debug('Remove exit code: %d', exit_code)

        if self.qube.is_running() and not self._initially_running:
            self.logger.info('Shutdown %s', self.qube.name)
            self.qube.shutdown()
            # FIXME: convert to self.vm.shutdown(wait=True) in core3
            while self.qube.is_running():
                time.sleep(1)

        self.__connected = False

    def transfer_agent(self, src_dir):
        """
        Copy a directory content to the workdir in the qube.

        Only files will be copied (without subdirectories).

        :param src_dir: str: path to local (dom0) directory
        """
        assert self.__connected  # open the connection first

        path_mapping = self._map_paths(src_dir)

        command = "qvm-run --pass-io {} 'mkdir -p {}'\n".format(
            self.qube, self.dest_dir)
        for src_path, dest_path in path_mapping.items():
            command_line = \
                "cat {} | qvm-run --pass-io {} 'cat > {}'".format(
                    src_path, self.qube, dest_path)
            command += command_line + "\n"
        self.logger.debug("RUN COMMAND: %s", command)
        os.system(command)

    def _map_paths(self, src_dir):
        result = {join(src_dir, file): join(self.dest_dir, file)
                  for file in os.listdir(src_dir)
                  if isfile(join(src_dir, file))}
        return result

    def run_entrypoint(self, entrypoint_path, force_color, *args):
        """
        Run a script in the qube.

        :param entrypoint_path: str: path to the entrypoint in the qube
        :param force_color: bool
        :return: Tuple[int, str]: return code and output of the script
        """
        entrypoint_args = " ".join(args)
        command = 'chmod u+x {}\n{} {}'.format(  # TODO test
                entrypoint_path,
                entrypoint_path,
                entrypoint_args
        )
        self.logger.debug("RUN COMMAND: %s", command)
        exit_code, output = QubeConnection._run_shell_command_in_qube(
            self.qube, command, force_color
        )

        return exit_code, output

    @staticmethod
    def _run_shell_command_in_qube(target, command, force_color=False):
        p = target.run_service('qubes.VMRootShell', user='root')
        untrusted_stdout_and_stderr = p.communicate(command.encode())
        return (p.returncode,
                QubeConnection._collect_output(
                    *untrusted_stdout_and_stderr, force_color=force_color)
                )

    @staticmethod
    def _collect_output(untrusted_stdout,
                        untrusted_stderr, force_color):
        untrusted_stdout = untrusted_stdout.decode('ascii', errors='ignore') + \
                           untrusted_stderr.decode('ascii', errors='ignore')

        if not force_color:
            # removing control characters, unless colors are enabled
            stdout_lines = [''.join([c for c in line if 0x20 <= ord(c) <= 0x7e])
                            for line in untrusted_stdout.splitlines()]
        else:
            stdout_lines = untrusted_stdout.splitlines()
        return stdout_lines
