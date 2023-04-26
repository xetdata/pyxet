# Integrations

[XetHub](https://xethub.com) is aimed to simplify every part of the data science workflow.   
Getting data in and out of XetHub is no exception.

* You can setup `XET_USER` and `XET_TOKEN` as an environment variable to avoid passing it to every function.

## Python Packages

### [pandas](https://pandas.pydata.org/)

```python
import pandas as pd
import pyxet # import to load

df = pd.read_csv("xet://username/repo/branch/data.csv")
```

### [Arrow](https://arrow.apache.org/)

```python
from pyxet.arrow import read_arrow
import pyarrow.dataset as ds

dataset = read_arrow('username/repo/branch/data.arrow') # returns a pyarrow.dataset
```

### [Polars](https://pola-rs.github.io/polars-book/user-guide/introduction.html)

You can use polars normally straight from XetHub.

```python
import polars as pl
import pyxet

df = pl.read_csv(pyxet.XetFS("xet://username/repo/main").open("data.csv"))
```

Using Arrow, we can use [lazy evaluation](https://pola-rs.github.io/polars-book/user-guide/lazy-api/intro.html) to avoid
downloading the whole dataset.

```python
import polars as pl
from pyxet.arrow import read_arrow

lazy_df = pl.scan_parquet(read_arrow('username/repo/branch/data.arrow'))
``` 


## [GitHub integration](https://github.com)

One way to use XetHub is to replace git altogether
by [migrating your repo to XetHub](https://xethub.com/assets/docs/migration/import-from-git).

An alternative is to use XetHub repo as a submodule, and use git as usual.   
The benefits of it is that it is minimal effort, and you get all the benefits of XetHub where needed.

```bash
project/ (GitHub)
├── data/ (XetHub)
├── models/ (XetHub)
├── notebooks/ (GitHub)
├── src/ (GitHub)
```

This let you manage your data and models as a part of your project instead of managing it on a blob-store like S3.   

You can do with the usual [git submodule commands](https://git-scm.com/book/en/v2/Git-Tools-Submodules).
```bash
git submodule add <xethub-repo-url>
```

