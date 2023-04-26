.. image:: images/logo.png
Welcome to pyxet's documentation!
=================================

pyxet is a Python library that provides a lightweight interface for the `XetHub <https://xethub.com/>`_  platform.
XetHub is a blob-store with a file-system like interface and git capabilities, therefore pyxet implement both a CLI for both a file-system and git needs.

Installation
~~~~~~~~~~~~
``pip install pyxet``


Features
~~~~~~~~
1. A file-system like interface.
    - [x] `fsspec <https://filesystem-spec.readthedocs.io>`_
    - [x] `pathlib.Path <https://docs.python.org/3/library/pathlib.html>`_
    - [ ] `glob <https://docs.python.org/3/library/glob.html>`_
2. Mount.
    - [x] read-only for data exploration and analysis
    - [ ] read-write for data ingestion and preparation - optimal for database backups and logs - coming soon
3. Integrations:
    - [x] `pandas <https://pandas.pydata.org>`_
    - [x] `polars <https://pola-rs.github.io/polars-book/>`_
    - [x] `pyarrow <https://arrow.apache.org/docs/python/>`_
    - [ ] `duckdb <https://duckdb.org>`_
4. Extra features like login, copy, move, delete, rename, etc.
5. Git capabilities:
    * add, commit, push
    * clone, fork
    * merge, rebase
    * pull, fetch
    * checkout, reset
    * stash, diff, log
    * status, branch
    * submodules
    * etc.

.. toctree::
   :maxdepth: 2
   :caption: Introduction:

   markdowns/quickstart

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   markdowns/filesystem
   markdowns/mount
   markdowns/integrations

.. toctree::
   :maxdepth: 2
   :caption: Use Cases:

   markdowns/collaboration
   markdowns/model_versioning
