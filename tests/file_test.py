import pyxet
from tests.utils import CONSTANTS
import time

def test_open_file():
    f = pyxet.open(CONSTANTS.TITANIC_CSV)
    start_time = time.time()
    print("--- %s seconds ---" % (time.time() - start_time))
    row = f.readline().decode()
    assert len(row.split(",")) == 12
    text = f.readall().decode()
    rows = text.split('\n')
    assert len(rows) == 892


def test_open_file_with_context_manager():
    with pyxet.open(CONSTANTS.TITANIC_CSV) as f:
        row = f.readline().decode()
        assert len(row.split(",")) == 12
        text = f.readall().decode()
        rows = text.split('\n')
        assert len(rows) == 892


def test_ls():
    assert len(pyxet.ls(CONSTANTS.TITANIC_MAIN)) == 6
    assert len(pyxet.ls(CONSTANTS.TITANIC_MAIN, detail=True)[0]) == 3
    assert len(pyxet.ls(CONSTANTS.TITANIC_MAIN + '/data')) == 2
    print(pyxet.ls(CONSTANTS.TITANIC_MAIN + '/data'))