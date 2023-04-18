import pyxet
from tests.utils import CONSTANTS


def test_ls():
    assert len(pyxet.ls(CONSTANTS.TITANIC_MAIN + '/data')) == 2
