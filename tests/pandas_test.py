import pyxet
from tests.utils import CONSTANTS, skip_if_no
import pyxet.file_system


@skip_if_no("pandas")
def test_pandas_csv():
    import pandas as pd
    with pyxet.open(CONSTANTS.TITANIC_CSV) as f:
        df = pd.read_csv(f)
    assert df.shape == (891, 12)

    head = pd.read_csv(pyxet.open(CONSTANTS.TITANIC_CSV), nrows=10)
    assert head.shape == (10, 12)

    assert len([chunk for chunk in pd.read_csv(pyxet.open(CONSTANTS.TITANIC_CSV), chunksize=10)]) == 90


@skip_if_no("pandas")
@skip_if_no("pyarrow")
def test_pandas_parquet():
    import pandas as pd

    with pyxet.open(CONSTANTS.TITANIC_PARQUET) as f:
        df = pd.read_parquet(f)
    assert df.shape == (891, 12)

    head = pd.read_parquet(pyxet.open(CONSTANTS.TITANIC_PARQUET), columns=["Survived", "Pclass"])
    assert head.shape == (891, 2)


@skip_if_no("pandas")
def test_pandas_json():
    import pandas as pd

    with pyxet.open(CONSTANTS.TITANIC_JSON) as f:
        df = pd.read_json(f)
    assert df.shape == (891, 12)
