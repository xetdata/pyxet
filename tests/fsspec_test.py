import fsspec
from tests.utils import CONSTANTS


def test_fsspec():
    fs = fsspec.filesystem("xet")
    assert str(fs.open(CONSTANTS.TITANIC_MAIN + '/readme.md').readline()).startswith("b'#")
    assert str(fs.open(CONSTANTS.TITANIC_MAIN + '/readme.md').readline()).startswith("b'#")
