from pyxet.pathlib import Path
from tests.utils import CONSTANTS
import pyxet


def test_pathlib_is_xet():
    assert not Path('').is_xet
    assert Path(CONSTANTS.TITANIC_JSON).is_xet


def test_pathlib_is_dir():
    assert Path(CONSTANTS.TITANIC_MAIN).is_dir()
    assert not Path(CONSTANTS.TITANIC_JSON).is_dir()


def test_pathlib_is_file():
    assert not Path(CONSTANTS.TITANIC_MAIN).is_file()
    assert Path(CONSTANTS.TITANIC_JSON).is_file()


def test_pathlib_read_text():
    with pyxet.open(CONSTANTS.TITANIC_JSON) as f:
        data = f.readall().decode()
    assert Path(CONSTANTS.TITANIC_JSON).read_text() == data


def test_pathlib_read_bytes():
    with pyxet.open(CONSTANTS.TITANIC_JSON) as f:
        data = f.readall()
    assert Path(CONSTANTS.TITANIC_JSON).read_bytes() == data


def test_pathlib_joinpath():
    assert Path(CONSTANTS.TITANIC_MAIN).joinpath('test').path == CONSTANTS.TITANIC_MAIN + '/test'


def test_pathlib_glob():
    assert len(Path(CONSTANTS.TITANIC_MAIN).glob('*.json')) == 1


def test_pathlib_iterdir():
    assert len(list(Path(CONSTANTS.TITANIC_MAIN).iterdir())) == 8


# TODO - manage if applying to local files too
def test_pathlib_absolute():
    assert Path(CONSTANTS.TITANIC_MAIN).absolute().path == Path(CONSTANTS.TITANIC_MAIN).path


def test_pathlib_exists():
    assert Path(CONSTANTS.TITANIC_MAIN).exists()
    assert not Path(CONSTANTS.TITANIC_MAIN + '/test').exists()


def test_pathlib_match():
    assert Path(CONSTANTS.TITANIC_CSV).match(r".*\.csv")
    assert not Path(CONSTANTS.TITANIC_JSON).match(r".*\.csv")


def test_pathlib_name():
    assert Path(CONSTANTS.TITANIC_CSV).name == "titanic.csv"


def test_pathlib_repo():
    assert Path(CONSTANTS.TITANIC_MAIN).repo == 'titanic.git'
    assert Path(CONSTANTS.TITANIC_MAIN + '/blabla').repo == 'titanic.git'
    assert Path('blabla').repo is None


def test_pathlib_user():
    assert Path(CONSTANTS.TITANIC_MAIN).user == 'xdssio'
    assert Path(CONSTANTS.TITANIC_MAIN + '/blabla').user == 'xdssio'
    assert Path('blabla').user is None


def test_pathlib_branch():
    assert Path(CONSTANTS.TITANIC_MAIN).branch == 'main'
    assert Path(CONSTANTS.TITANIC_MAIN + '/blabla').branch == 'main'
    assert Path('blabla').branch is None


def test_pathlib_remote():
    assert Path(CONSTANTS.TITANIC_MAIN).remote == 'https://xethub.com'


# TODO - work with local files and missing remote cases
def test_pathlib_parent():
    assert Path(CONSTANTS.TITANIC_MAIN).parent.path == 'https://xethub.com/xdssio/titanic.git'
    assert Path(CONSTANTS.TITANIC_CSV).parent.path == 'https://xethub.com/xdssio/titanic.git/main'
    assert Path(
        CONSTANTS.TITANIC_MAIN + '/data/titanic_0.parquet').parent.path == 'https://xethub.com/xdssio/titanic.git/main/data'
