import pyxet
from tests.utils import CONSTANTS


def test_open_file():
    f = pyxet.open(CONSTANTS.TITANIC_CSV)
    row = f.readline().decode()
    assert len(row.split(",")) == 12
    text = f.readall().decode()
    rows = text.split('\n')
    assert len(rows) == 892
    assert len(rows[0].split(",")) == 13
    # TODO why is this 13? but when read as line it's 12?


def test_open_file_with_context_manager():
    with pyxet.open(CONSTANTS.TITANIC_CSV) as f:
        row = f.readline().decode()
        assert len(row.split(",")) == 12
        text = f.readall().decode()
        rows = text.split('\n')
        assert len(rows) == 892
        assert len(rows[0].split(",")) == 13


def test_ls():
    assert len(pyxet.ls(CONSTANTS.TITANIC_MAIN)) == 6
    assert len(pyxet.ls(CONSTANTS.TITANIC_MAIN, detail=True)[0]) == 3
