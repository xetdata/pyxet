# Python integrations

## [Pandas](https://pandas.pydata.org)
```python
import pyxet
import pandas as pd

with pyxet.open("https://xethub.com/xdssio/titanic.git/main/titanic.csv") as f:
    df = pd.read_csv(f)
```

## [Arrow](https://arrow.apache.org)
```python
import pyxet
dataset = pyxet.read_arrow("https://xethub.com/xdssio/titanic.git/main/titanic.parquet")
```

## [Polars](https://polars.rs)
```python
import pyxet
import polars as pl

with pyxet.open("https://xethub.com/xdssio/titanic.git/main/titanic.csv") as f:
    df = pl.read_csv(f)
    
# Lazy evaluation using arrow
import polars as pl
lazy_df = pl.scan_ds(pyxet.read_arrow("https://xethub.com/xdssio/titanic.git/main/titanic.parquet"))
```