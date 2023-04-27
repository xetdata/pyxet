# File system

Filesystem APIs are straightforward and based on the [fsspec](https://filesystem-spec.readthedocs.io/en/latest/) library. This means that you can use
the same API to access local files, remote files, and files in XetHub.

## [Filesystem (fsspec)](https://filesystem-spec.readthedocs.io/en/latest/usage.html)

* [Copy conventions](https://filesystem-spec.readthedocs.io/en/latest/copying.html)

`pyxet.XetFS` returns a filesystem object that can be used with fsspec. It enables you to work with your repository 
like a normal filesystem in read-only mode. Coming soon: support for write and Git commands.

```python
import pyxet

fs = pyxet.XetFS("https://xethub.com/xdssio/titanic-server-example/main", login=..., **kwargs)

fs.ls("path/to/dir")
fs.glob("path/to/dir/*")

# Currently supported: read-only filesystem operations
with fs.open("path/data.csv", 'b') as f:
    f.read()

    ...

# Coming soon: write support!
with fs.commit("message"):
    with fs.open("path/file.txt", 'w') as f:
        f.write("Hello, world!")
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
path.absolute()
path.iterdir()
path.joinpath()  # returns a new path
path.glob()  # use fsspec glob
# work-in-progress
path.write_text("text")
path.write_bytes(b"text")
```
