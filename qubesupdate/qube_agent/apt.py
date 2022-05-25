import logging

from utils import compare_packages, run_cmd


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def _refresh():
    """
    # TODO
    """
    cmd = ["sudo",
           "apt-get",
           "-q",
           "update"
           ]

    ret_code, stdout, stderr = run_cmd(cmd)

    if ret_code != 0:
        # raise RuntimeError(stderr)  # TODO: silent mode?
        log.error("ERROR: %s", stderr)

    # TODO handle errors


def get_packages():
    """
    # TODO
    """

    cmd = [
        "dpkg-query",
        "--showformat",
        "${Status} ${Package} ${Version}\n",
        "-W",
    ]

    retcode, stdout, stderr = run_cmd(cmd)
    # install ok installed openssl 1.1.1n-0+deb11u2

    packages = {}
    for line in stdout.splitlines():  # TODO
        cols = line.split()
        try:
            selection, flag, status, package, version = cols
        except (ValueError, IndexError):
            continue

        if cols:
            if selection in ("install", "hold") and status == "installed":
                packages.setdefault(package, []).append(version)

    return packages


def upgrade(refresh=True, remove=False):
    """
    # TODO
    """
    if refresh:
        _refresh()

    old_pkg = get_packages()

    cmd = ["sudo",
           "apt-get",
           "-q",
           "-y",
           "dist-upgrade" if remove else "upgrade"]
    # TODO flags?

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
