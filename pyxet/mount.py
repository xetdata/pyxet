import subprocess
from pyxet.utils import shell


def mount(uri: str, target: str = '.', stdout=subprocess.DEVNULL, **kwargs):
    return shell(commnad=f"git xet mount {uri} {target}", stdout=stdout, **kwargs)


def umount(uri: str, **kwargs):
    return shell(commnad=f"umount {uri}", **kwargs)
