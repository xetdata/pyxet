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


def test_write_model_pickle():
    import pickle
    class Model:
        def __init__(self, a):
            self.a = a
    fs = pyxet.repo(CONSTANTS.TESTING_TEMPDIR)
    file_path = CONSTANTS.TESTING_TEMPDIR + 'model.pickle'
    with fs.commit("upload pickle model"):
        pickle.dump(model(), fs.open(file_path, 'wb'))
    loaded = pickle.load(fs.open(file_path, 'rb'))
    assert loaded.a == 1


def test_read_write():
    repo = "https://_xethub_testing_account:q8HnHwaw6hw3zhJNuUjAnw@xethub.com/_xethub_testing_account/read_write_testing.git/main"

    fs = pyxet.repo(repo)

    import hashlib
    import time

    test_data = hashlib.md5(str(time.time()).encode('utf-8')).hexdigest()

    with fs.commit("change test_data.dat"):
        f = fs.open("test_data.dat", "w")
        f.write(test_data)
        f.close()

    f = fs.open("test_data.dat", "r")
    assert f.read() == test_data
