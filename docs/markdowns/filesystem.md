# File system

Pyxet implements a simple and intuitive API based on the [fsspec](https://filesystem-spec.readthedocs.io/en/latest/)
library.
Use the same API to access local files, remote files, and files in XetHub. All operations are currently read-only; write
functionality
is in development.

## Using URLs

Xet URLs should be of the form `xet://<repo_user>/<repo_name>/<branch>/<path-to-file>`, where `<path-to-file>` is
optional if the URL
refers to a repository. The xet:// prefix is not neccery when using pyxet.XetFS.

## pyxet.XetFS

To work with a XetHub repository as a file system, you can use the `pyxet.XetFS` class. This class provides a file
system handle
for a XetHub repository, allowing you to perform read-only operations like ls, glob, and open. The initialization of
this class
requires a repository URL and optional arguments for branch, user, and token.

Example usage of `pyxet.XetFS`:

```sh
  import pyxet

  # Create a file system handle for a public repository.
  fs = pyxet.XetFS()

  # List files in the repository.
  files = fs.ls('xet://XetHub/Flickr30k/main')

  # Open a file from the repository.
  f = fs.open('xet://XetHub/Flickr30k/main/results.csv')

  # Read the contents of the file.
  contents = f.read()
```
## Other common utils
```python
import pyxet

fs = pyxet.XetFS()  # fsspec filesystem

# Reads
fs.info(
    "xdssio/titanic/main/titanic.csv")  # {'name': 'https://xethub.com/main/titanic.csv', 'size': 61194, 'type': 'file'}
fs.open("xdssio/titanic/main/titanic.csv", 'r').read(11)  # 'PassengerId'
fs.get("xdssio/titanic/main/data/*parquet", "data", recursive=True)  # Download file/directories recursively
fs.cp("xdssio/titanic/main/titanic.csv", "titanic.csv")  # fsspec cp
fs.ls("xdssio/titanic/main/data/", detail=False)  # ['data/titanic_0.parquet', 'data/titanic_1.parquet']

# Writes - You need to have write permissions to that repo
with fs.transaction("xdssio/titanic/main"):
    fs.open("xdssio/titanic/main/text.txt", 'w').write("Hello World")
with fs.transaction("xdssio/titanic/main"):
    fs.cp("xdssio/titanic/main/titanic.csv", "xdssio/titanic/main/titanic2.csv")
fs.info(
    "xdssio/titanic/main/titanic2.csv")  # {'name': 'https://xethub.com/main/titanic2.csv', 'size': 61194, 'type': 'file'}
with fs.transaction("xdssio/titanic/main"):
    fs.rm("xdssio/titanic/main/titanic2.csv")
fs.info("xdssio/titanic/main/titanic2.csv")  # FileNotFoundError: xdssio / titanic / main / titanic2.csv
```

## [fsspec](https://filesystem-spec.readthedocs.io/en/latest/usage.html)

Many packages such as pandas and pyarrow support the fsspec protocol.
xet:// URLs must be used as file paths in these packages. For example, to read a csv from pandas, use:

```sh
  import pyxet # make xet protocol available to fsspec
  import pandas as pd

  df = pd.read_csv('xet://XetHub/Flickr30k/main/results.csv')
```

All fsspec read-only functionality is supported; write operations such as flush() and write() are in development.

