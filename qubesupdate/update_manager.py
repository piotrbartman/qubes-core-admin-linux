# coding=utf-8
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2022  Marek Marczykowski-Górecki
#                                   <marmarek@invisiblethingslab.com>
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
import sys
import logging
import multiprocessing
from os.path import join

import qubesadmin.vm
import qubesadmin.exc
from qube_connection import QubeConnection

FORMAT_LOG = '%(asctime)s %(message)s'
LOGPATH = '/var/log/qubes'
formatter_log = logging.Formatter(FORMAT_LOG)


class UpdateManager:
    """
    Update multiple qubes simultaneously.
    """

    def __init__(self, qubes, max_concurrency=4, show_output=False,
                 force_color=False):
        self.qubes = qubes
        self.max_concurrency = max_concurrency
        self.show_output = show_output
        self.force_color = force_color
        self.exit_code = 0

    def run(self):
        """
        Run simultaneously `update_qube` for all qubes as separate processes.
        """
        pool = multiprocessing.Pool(self.max_concurrency)
        for qube in self.qubes:
            pool.apply_async(update_qube,
                             (qube.name, self.show_output,
                              self.force_color),
                             callback=self.collect_result
                             )
        pool.close()
        pool.join()
        return self.exit_code

    def collect_result(self, result_tuple):
        """
        Callback method to process `update_qube` output.

        :param result_tuple: tuple(qube_name, exit_code, result)
        """
        qube_name, exit_code, result = result_tuple
        self.exit_code = max(self.exit_code, exit_code)
        if self.show_output and isinstance(result, list):
            sys.stdout.write(qube_name + ":\n")
            sys.stdout.write('\n'.join(['  ' + line for line in result]))
            sys.stdout.write('\n')
        else:
            print(qube_name + ": " + result)


def update_qube(qname, show_output, force_color):
    """
    Create and run `UpdateAgentManager` for qube.

    :param qname: name of qube
    :param show_output: flag, if true print full output
    :param force_color: flag, if true do not sanitize output
    :return:
    """
    app = qubesadmin.Qubes()
    try:
        qube = app.domains[qname]
    except KeyError:
        return qname, 2, "ERROR (qube not found)"
    try:
        runner = UpdateAgentManager(app, qube, force_color=force_color)
        exit_code, result = runner.run_agent(return_output=show_output)
    except Exception as e:  # pylint: disable=broad-except
        return qname, 1, "ERROR (exception {})".format(str(e))
    return qube.name, exit_code, result


class UpdateAgentManager:
    """
    Send update agent files and run it in the qube.
    """
    AGENT_RELATIVE_DIR = "qube_agent"
    ENTRYPOINT = "updater_agent"

    def __init__(self, app, qube, force_color=False, loglevel='NOTSET'):
        self.qube = qube
        self.app = app
        self.log = logging.getLogger('qubesupdate.qube.' + qube.name)
        self.log_path = os.path.join(LOGPATH, 'update-{}.log'.format(qube.name))
        handler_log = logging.FileHandler(
            self.log_path,
            encoding='utf-8')
        handler_log.setFormatter(formatter_log)
        self.log.addHandler(handler_log)
        self.log.setLevel(loglevel)
        self.log.propagate = False
        self.force_color = force_color

    def run_agent(self, return_output, *args):
        self.log.debug('Running update agent for {}'.format(self.qube.name))
        dest_dir = "/tmp/qubesupdate/"
        dest_agent = os.path.join(dest_dir, UpdateAgentManager.ENTRYPOINT)
        this_dir = os.path.dirname(os.path.realpath(__file__))
        src_dir = join(this_dir, UpdateAgentManager.AGENT_RELATIVE_DIR)

        with QubeConnection(self.qube, dest_dir, self.log) as qc:
            self.log.debug("Transferring files to destination qube: {}".format(
                self.qube.name))
            qc.transfer_agent(src_dir)

            self.log.debug("The agent is starting the task in qube: {}".format(
                self.qube.name))
            exit_code, output = qc.run_entrypoint(
                dest_agent, self.force_color, *args)

            # TODO handle logs

            for line in output:
                self.log.info('output: %s', line)
            self.log.info('exit code: %d', exit_code)

            if return_output and output:
                return_data = output
            else:
                return_data = "OK" if exit_code == 0 else \
                    "ERROR (exit code {}, details in {})".format(
                        exit_code, self.log_path)

        return exit_code, return_data