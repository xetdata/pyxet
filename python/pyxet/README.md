# pyxet: Python bindings for Xethub

## What is it?
pyxet is a Python library that provides a lightweight interface for the [XetHub](https://xethub.com/) platform.

## Main features
1. A filesystem interface.
    * [fssspec](https://filesystem-spec.readthedocs.io)
        * copy
        * remove
        * list
        * etc.
    * [glob](https://docs.python.org/3/library/glob.html)
    * [pathlib.Path](https://docs.python.org/3/library/pathlib.html)(WIP)
2. Mount.
    * Read-only optimize for speed; perfect for data exploration and analysis and building data-apps and model
      inference.
3. Integrations:
    - [x] [GitHub](https://github.com) [submodule](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
    - [x] [pandas](https://pandas.pydata.org)
    - [x] [polars](https://pola-rs.github.io/polars-book/)
    - [x] [pyarrow](https://arrow.apache.org/docs/python/)
    - [ ] [duckdb](https://duckdb.org/)
    - [ ] [dask](https://dask.org/)
    - [ ] [ray](https://ray.io/)

For API documentation and full examples, please see the [documentation](https://pyxet.readthedocs.io/en/latest/)

## Where to get it
```sh
git config --global user.name "Foo Bar"
git config --global user.email "foo@bar.com"
pip install pyxet
```
## License
[BSD 3](LICENSE)

## Getting Help
Go to the [GitHub project](https://github.com/xetdata/pyxet/), join the
[Discord server](https://discord.gg/KCzmjDaDdC), and file
[issues](https://github.com/xetdata/pyxet/issues)

Development Environment
-----------------------
To set up build env, switch to this directory and run:
```
python -m venv .env
source .env/bin/activate
pip install maturin
pip install fsspec
pip install ipython (for convenience)
```

To develop:
```
source ./develop.sh
```

To build locally
```
maturin develop
```


Then running python and import pyxet should work

See https://www.maturin.rs/develop.html for details

Building a release
------------------
On mac:
```
MACOSX_DEPLOYMENT_TARGET=10.9 maturin build --release --target universal2-apple-darwin
```
