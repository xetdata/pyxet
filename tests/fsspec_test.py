import pyxet
import fsspec
from tests.utils import CONSTANTS


def test_fsspec():
    fs = fsspec.filesystem("xet", url_info=CONSTANTS.TITANIC_MAIN)
    assert str(fs.open(CONSTANTS.TITANIC_MAIN + '/readme.md').readline()).startswith("b'#")
    assert str(fs.open(CONSTANTS.TITANIC_MAIN + '/readme.md').readline()).startswith("b'#")

    # https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.glob
    listing = fs.glob(CONSTANTS.TITANIC_MAIN)
    assert listing == ['/']

    listing = fs.glob(CONSTANTS.TITANIC_MAIN + '/data')
    assert listing == ['data']

    listing = fs.glob(CONSTANTS.TITANIC_MAIN + '/data/')
    assert listing == ['data/titanic_0.parquet', 'data/titanic_1.parquet']

    listing = fs.glob(CONSTANTS.TITANIC_MAIN + '/data/*')
    assert listing == ['data/titanic_0.parquet', 'data/titanic_1.parquet']

    listing = fs.glob(CONSTANTS.TITANIC_MAIN + '/data/*parquet')
    assert listing == ['data/titanic_0.parquet', 'data/titanic_1.parquet']

    listing = fs.glob(CONSTANTS.TITANIC_MAIN + '/data/titanic*')
    assert listing == ['data/titanic_0.parquet', 'data/titanic_1.parquet']

    listing = fs.glob(CONSTANTS.TITANIC_MAIN + '/data/*1.parquet')
    assert listing == ['data/titanic_1.parquet']

    listing = fs.glob(CONSTANTS.TITANIC_MAIN + '/**/*parquet')
    assert listing == ['data/titanic_0.parquet', 'data/titanic_1.parquet']

    listing = fs.glob(CONSTANTS.TITANIC_MAIN + '/titanic*')
    assert listing == ['titanic.csv', 'titanic.json', 'titanic.parquet']