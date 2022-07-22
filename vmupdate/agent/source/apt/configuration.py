from .allow_releaseinfo_change import allow_releaseinfo_change


def get_configured_apt(os_data, requirements, logpath):
    try:
        from .apt_api import APT
    except ImportError:
        # no progress reporting
        from .apt_cli import APTCLI as APT

    allow_releaseinfo_change(os_data)
    return APT(logpath)
