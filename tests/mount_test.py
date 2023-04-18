import pathlib
from pyxet.mount import mount, umount
from tests.utils import CONSTANTS
import os
import shutil

TMP = 'tmp'
"""
Can't use tempfile.TemporaryDirectory because of permissions issues
"""


def test_mount():
    os.mkdir(TMP)
    mount(CONSTANTS.TITANIC_MOUNT, TMP)
    path = pathlib.Path(TMP)
    assert len(list(path.iterdir())) == 5
    umount(TMP)
    assert len(list(path.iterdir())) == 0
    shutil.rmtree(TMP, ignore_errors=True)
