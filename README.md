Python bindings for Xethub
==========================

Development Environment
-----------------------
To set up build env, switch to this directory and run:
```
python -m venv .env
source .env/bin/activate
pip install maturin fsspec ipython pytest

# we need a better way to use the rust stuff
git submodule add https://github.com/xetdata/xethub.git   # if not already done
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

Usage
-----
```
import pyxet
f = pyxet.open("https://xethub.com/xdssio/langchain_demo.git/main/app.py")
f.readlines()
f = pyxet.open("https://xethub.com/xdssio/langchain_demo.git/main/readme.md")
f.readlines()
```
Opening different files in the same repo but different branches is relatively
inexpensive. (The repo only needs to be cloned once).

Docs
----
cd docs
make html

look at docs/_build/html/index.html


Building a release
------------------
On mac:
```
maturin build --release --target universal2-apple-darwin
