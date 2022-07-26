#!/usr/bin/python3
import argparse
import sys

from pathlib import Path

from source.args import add_arguments
from source.apt.configuration import get_configured_apt
from source.dnf.configuration import get_configured_dnf
from source.utils import get_os_data


LOGPATH = '/var/log/qubes/qubes-update'
Path(LOGPATH).mkdir(parents=True, exist_ok=True)


def parse_args(args):
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args(args)
    return args


def main(args=None):
    """
    Run the appropriate package manager.

    :param args: # TODO
    """
    args = parse_args(args)
    os_data = get_os_data()
    requirements = {}
    refresh_args = []
    upgrade_args = []

    if os_data["os_family"] == "Debian":
        pkg_mng = get_configured_apt(os_data, requirements, LOGPATH, args.log)
    elif os_data["os_family"] == "RedHat":
        pkg_mng = get_configured_dnf(os_data, requirements, LOGPATH, args.log)
    else:
        raise NotImplementedError(
            "Only Debian and RedHat based os is supported.")

    # TODO config here
    return_code = pkg_mng.upgrade(refresh=True,
                                  hard_fail=True,
                                  remove_obsolete=True,
                                  requirements=requirements,
                                  refresh_args=refresh_args,
                                  upgrade_args=upgrade_args)
    # TODO clean config

    return return_code


if __name__ == '__main__':
    sys.exit(main())
