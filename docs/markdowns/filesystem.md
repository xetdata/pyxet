# File system

The file system APIs are the most straight forward. They are based on the [fsspec](https://filesystem-spec.readthedocs.io/en/latest/) library. This means that you can use the same API to access local files, remote files, and files in Xethub.

## CLI-like
```python
import pyxet
# copy, move, remove,  - TODO
pyxet.cp()
pyxet.rm()
pyxet.mv()
pyxet.ls()
pyxet.info()
pyxet.login()
```
## Open a file
```python
# read a file
import pyxet
with pyxet.open("https://xethub.com/xdssio/titanic.git/main/titanic.csv") as f:
    f.readline()
    f.readlines()
    f.readall()
```
## [pathlib](https://docs.python.org/3/library/pathlib.html)
```python
from pyxet.pathlib import Path

path = Path("https://xethub.com/xdssio/titanic.git/main/titanic.csv")
path.is_dir()
path.is_file()
path.exists()
path.read_bytes()
path.read_text()
path.write_text("text") # TODO
path.write_bytes(b"text") # TODO
```

## [fsspec](https://filesystem-spec.readthedocs.io/en/latest/)
```python
import fsspec
fs = fsspec.filesystem("xet")
with fs.open("https://xethub.com/xdssio/titanic.git/main/titanic.csv") as f:
    f.readline()
    ...
```

## [glob](https://docs.python.org/3/library/glob.html)
```python
from pyxet.glob import glob
glob("https://xethub.com/xdssio/titanic.git/main/data/*.csv")

```