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
from os.path import join
import shutil
import tempfile
from subprocess import CalledProcessError

from vmupdate.agent.source.args import AgentArgs


class QubeConnection:
    """
    Run scripts in the qube.

    1. Initialize the state of connection.
    2. Transfer files to a new directory, start the qube if not running.
    3. Run an entrypoint script, return the output.
    4. On close, remove the created directory,
       stop the qube if it was started by this connection.
    """

    def __init__(self, qube, dest_dir, cleanup, logger):
        self.qube = qube
        self.dest_dir = dest_dir
        self.cleanup = cleanup
        self.logger = logger
        self._initially_running = None
        self.__connected = False

    def __enter__(self):
        self._initially_running = self.qube.is_running()
        self.__connected = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cleanup:
            self.logger.info('Remove %s', self.dest_dir)
            self._run_shell_command_in_qube(
                self.qube, ['rm', '-r', self.dest_dir])

        if self.qube.is_running() and not self._initially_running:
            self.logger.info('Shutdown %s\n', self.qube.name)
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

        arch_format = ".tar.gz"

        arch_dir = tempfile.mkdtemp()
        root_dir = os.path.dirname(src_dir)
        base_dir = os.path.basename(src_dir.strip(os.sep))
        src_arch = join(arch_dir, base_dir + arch_format)
        dest_arch = join(self.dest_dir, base_dir + arch_format)
        shutil.make_archive(base_name=join(arch_dir, base_dir),
                            format='gztar', root_dir=root_dir,
                            base_dir=base_dir)

        run_cmd = f"qvm-run --user=root --pass-io {self.qube.name} "

        command = run_cmd + f"'mkdir -p {self.dest_dir}'"
        self.logger.debug("RUN COMMAND: %s", command)
        os.system(command)

        command = f"cat {src_arch} | " + \
                  run_cmd + f"'cat > {dest_arch}'"
        self.logger.debug("RUN COMMAND: %s", command)
        os.system(command)

        command = run_cmd + f"'cd {self.dest_dir}; " \
                            f"tar -xzf {dest_arch}'"
        self.logger.debug("RUN COMMAND: %s", command)
        os.system(command)

    def run_entrypoint(self, entrypoint_path, force_color, agent_args):
        """
        Run a script in the qube.

        :param entrypoint_path: str: path to the entrypoint.py in the qube
        :param force_color: bool
        :param agent_args: args for agent entrypoint
        :return: Tuple[int, str]: return code and output of the script
        """
        # make sure entrypoint is executable
        command = ['chmod', 'u+x', entrypoint_path]
        self.logger.debug("RUN COMMAND: %s", command)
        exit_code, output = self._run_shell_command_in_qube(
            self.qube, command, force_color
        )

        # run entrypoint
        command = [entrypoint_path, *AgentArgs.to_cli_args(agent_args)]
        self.logger.debug("RUN COMMAND: %s", command)
        exit_code_, output_ = self._run_shell_command_in_qube(
            self.qube, command, force_color
        )
        exit_code = max(exit_code, exit_code_)
        output += output_

        return exit_code, output

    def _run_shell_command_in_qube(self, target, command, force_color=False):
        try:
            untrusted_stdout_and_stderr = target.run_with_args(*command,
                                                               user='root')
            returncode = 0
        except CalledProcessError as e:
            self.logger.error(str(e))
            returncode = e.returncode
            untrusted_stdout_and_stderr = (b"", b"")
        # TODO print to console
        #         p.stdin.write((command + "\n").encode())
        #         p.stdin.close()
        #         while True:
        #             outline = p.stdout.readline()
        #             errline = p.stderr.readline()
        #             if not outline and not errline:
        #                 break
        #             if outline:
        #                 print(outline.decode())
        #             if errline:
        #                 print(errline)
        #         p.stdout.close()
        #         p.stderr.close()
        #         p.wait()
        #         untrusted_stdout_and_stderr = ("".encode(), "".encode()) #p.communicate(command.encode())
        return returncode, QubeConnection._collect_output(
            *untrusted_stdout_and_stderr, force_color=force_color)

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
