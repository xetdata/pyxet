from tests.utils import CONSTANTS
import pyxet.glob


def test_listdir():
    assert len(list(pyxet.glob._listdir(CONSTANTS.TITANIC_MAIN))) == 8
    assert len(list(pyxet.glob._listdir(CONSTANTS.TITANIC_MAIN + '/'))) == 8
    assert len(list(pyxet.glob._listdir(CONSTANTS.TITANIC_MAIN + '/data'))) == 2


def test_glob():
    assert pyxet.glob.glob(CONSTANTS.TITANIC_MAIN) == [CONSTANTS.TITANIC_MAIN]
    assert pyxet.glob.glob(CONSTANTS.TITANIC_MAIN + '/') == [CONSTANTS.TITANIC_MAIN + '/']
    assert pyxet.glob.glob(CONSTANTS.TITANIC_MAIN + '*') == [CONSTANTS.TITANIC_MAIN]

    assert pyxet.glob.glob(CONSTANTS.TITANIC_MAIN + "/*") == [
        'https://xethub.com/xdssio/titanic.git/main/.gitattributes',
        'https://xethub.com/xdssio/titanic.git/main/dat',
        'https://xethub.com/xdssio/titanic.git/main/readme.md',
        'https://xethub.com/xdssio/titanic.git/main/titanic.csv',
        'https://xethub.com/xdssio/titanic.git/main/titanic.json',
        'https://xethub.com/xdssio/titanic.git/main/titanic.parquet']
    assert pyxet.glob.glob(CONSTANTS.TITANIC_MAIN + "/data") == [CONSTANTS.TITANIC_MAIN + '/data']
    assert pyxet.glob.glob(CONSTANTS.TITANIC_MAIN + "/data/") == [CONSTANTS.TITANIC_MAIN + '/data/']
    assert pyxet.glob.glob(CONSTANTS.TITANIC_MAIN + "/data/*") == [
        'https://xethub.com/xdssio/titanic.git/main/data/titanic_0.parquet',
        'https://xethub.com/xdssio/titanic.git/main/data/titanic_1.parquet']
    assert pyxet.glob.glob(CONSTANTS.TITANIC_MAIN + "/data/*.parquet") == [
        'https://xethub.com/xdssio/titanic.git/main/data/titanic_0.parquet',
        'https://xethub.com/xdssio/titanic.git/main/data/titanic_1.parquet']
    assert pyxet.glob.glob(CONSTANTS.TITANIC_MAIN + "/data/*1.parquet") == [
        'https://xethub.com/xdssio/titanic.git/main/data/titanic_1.parquet']
    assert pyxet.glob.glob(CONSTANTS.TITANIC_MAIN + "/**/*.parquet") == [
        'https://xethub.com/xdssio/titanic.git/main/data/titanic_0.parquet',
        'https://xethub.com/xdssio/titanic.git/main/data/titanic_1.parquet']

    assert pyxet.glob.glob(CONSTANTS.TITANIC_MAIN + "/titanic*") == [
        'https://xethub.com/xdssio/titanic.git/main/titanic.csv',
        'https://xethub.com/xdssio/titanic.git/main/titanic.json',
        'https://xethub.com/xdssio/titanic.git/main/titanic.parquet']
    assert pyxet.glob.glob(CONSTANTS.TITANIC_MAIN + "/*.csv") == [
        'https://xethub.com/xdssio/titanic.git/main/titanic.csv']

    # TODO bug
    assert pyxet.glob.glob(CONSTANTS.TITANIC_MAIN + "*.json") == [
        'https://xethub.com/xdssio/titanic.git/main/titanic.json']
