import pyxet
from tests.utils import CONSTANTS, skip_if_no


@skip_if_no("polars")
def test_polars_read_csv():
    import polars as pl

    with pyxet.open(CONSTANTS.TITANIC_CSV) as f:
        df = pl.read_csv(f)
    assert df.shape == (891, 12)

    head = pl.read_csv(pyxet.open(CONSTANTS.TITANIC_CSV), n_rows=10)
    assert head.shape == (10, 12)


@skip_if_no("polars")
def test_polars_read_parquet():
    import polars as pl

    with pyxet.open(CONSTANTS.TITANIC_PARQUET) as f:
        df = pl.read_parquet(f)
    assert df.shape == (891, 12)

    with pyxet.open(CONSTANTS.TITANIC_PARQUET) as f:
        head = pl.read_parquet(f, columns=["Survived", "Pclass"], n_rows=10)
    assert head.shape == (10, 2)


@skip_if_no("polars")
def test_polars_scan_csv():
    import polars as pl

    with pyxet.open(CONSTANTS.TITANIC_CSV) as f:
        df = pl.scan_csv(f)
    assert df.shape == (891, 12)


@skip_if_no("pyarrow")
@skip_if_no("polars")
def test_polars_scan_parquet():
    """
    To use polars lazy evaluation, we need to use pyarrow.dataset to read the parquet file.
    """
    import pyarrow.dataset as ds
    import polars as pl

    fs = pyxet.XetFS(url_info=CONSTANTS.TITANIC_MAIN)
    dataset = ds.dataset(CONSTANTS.TITANIC_PARQUET, filesystem=fs)
    lazy_df = pl.scan_pyarrow_dataset(dataset)
    assert lazy_df.select(pl.count('Name')).collect()['Name'].to_list()[0] == 891
