import logging
import shutil

from utils import compare_packages, run_cmd

log = logging.getLogger(__name__)


def get_package_manager():
    """
    # TODO
    """
    pck_mng = shutil.which('dnf')
    if pck_mng is not None:
        return 'dnf'
    pck_mng = shutil.which('yum')
    if pck_mng is not None:
        return 'yum'

    return None  # TODO


def get_packages():
    """
    # TODO
    """

    cmd = [
        "rpm",
        "-qa",
        "--queryformat",
        "%{NAME} %{VERSION}%{RELEASE}\n",
    ]
    ret_code, stdout, stderr = run_cmd(cmd)

    packages = {}
    for line in stdout.splitlines():  # TODO
        cols = line.split()
        try:
            package, version = cols
        except (ValueError, IndexError):
            continue

        if cols:
            packages.setdefault(package, []).append(version)

    return packages


def _refresh():
    """
    # TODO
    """
    cmd = [get_package_manager(),
                 "-q",
                 "-y",
                 "clean",
                 "expire-cache"]
    ret_code, stdout, stderr = run_cmd(cmd)

    if ret_code != 0:
        # raise RuntimeError(stderr)  # TODO: silent mode?
        log.error("ERROR: %s", stderr)

    cmd = [get_package_manager(),
                  "-q",
                  "-y",
                  "check-update"]
    ret_code, stdout, stderr = run_cmd(cmd)

    if ret_code != 0:
        # raise RuntimeError(stderr)  # TODO: silent mode?
        log.error("ERROR: %s", stderr)

    # TODO handle errors


# TODO unifying with apt
def upgrade(refresh=True, remove=False):
    """
    # TODO
    """

    if refresh:
        _refresh()

    old_pkg = get_packages()

    cmd = [get_package_manager(),
           "-q",
           "-y"]
    # TODO: flags

    if remove:
        cmd.append("upgrade")  # TODO handle remove for dnf
    else:
        if get_package_manager() == "dnf":
            cmd.append("upgrade")
        else: # yum
            cmd.append("update")

    ret_code, stdout, stderr = run_cmd(cmd)  # TODO sync progress

    new_pkg = get_packages()

    changes = compare_packages(old=old_pkg, new=new_pkg)

    for pkg in changes["updated"]:
        log.debug("%s %s->%s",
                  pkg,
                  changes["updated"][pkg]["old"],
                  changes["updated"][pkg]["new"]
                  )

    # TODO: gather logs if ret_code != 0

    return ret_code
