from tests.utils import skip_if_no

import pytest


@skip_if_no("duckdb")
@pytest.fixture(autouse=True)
def run_before_and_after_tests(tmpdir):
    """Fixture to execute asserts before and after a test is run"""
    import duckdb
    con = duckdb.connect(database=":memory:")
    con.execute("INSTALL 'httpfs';")

    yield


@skip_if_no("duckdb")
def test_duckdb():
    import duckdb
    nrows = 10
    url = "https://xethub.com/xdssio/titanic.git/main/titanic.parquet"
    df = duckdb.query(f'SELECT * FROM "{url}" LIMIT {nrows};').df()
