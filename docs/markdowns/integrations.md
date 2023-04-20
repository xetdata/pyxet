# Python integrations
[XetHub](https://xethub.com) is aimed to simplify every part of the data science workflow.   
Getting data in and out of XetHub is no exception.
* You can setup `XETHUB_TOKEN` as an environment variable to avoid passing it to every function.

## Packages

### [pandas](https://pandas.pydata.org/)
```python
import pandas as pd

df = pd.read_csv("xet://username/repo/main/data.csv", xet={"access_token" : "..."})
df.to_csv("xet://username/repo/main/data.csv", index=False)
```
### [Arrow](https://arrow.apache.org/)
```python
import pyxet
import pyarrow.dataset as ds

dataset = ds.dataset("titanic.parquet", 
                     filesystem=pyxet.repo("user/repo","branch"))
```
### [Polars](https://pola-rs.github.io/polars-book/user-guide/introduction.html)
You can use polars normally straight from XetHub.
```python
import polars as pl

df = pl.read_csv("xet://username/repo/main/data.csv")
df.write_csv("xet://username/repo/main/data.csv")
```
Using Arrow, we can use [lazy evaluation](https://pola-rs.github.io/polars-book/user-guide/lazy-api/intro.html) to avoid downloading the whole dataset.
```python

import pyxet
import pyarrow.dataset as ds
lazy_df = pl.scan_parquet(ds.dataset("titanic.parquet", 
                                     filesystem=pyxet.repo("user/repo","branch")))
``` 
### [DuckDB](https://duckdb.org) (WIP)