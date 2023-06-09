.. image:: images/logo.png
  :width: 250
  :alt: pyxet logo

Welcome to pyxet's documentation!
=================================

pyxet is a Python package that provides a lightweight interface for the `XetHub <https://xethub.com/>`_  platform with familiar 
file system operations and integrations with common tools. It works with anything that supports fsspec and more integrations are planned.

1. A file-system like interface:
    - [x] `fsspec <https://filesystem-spec.readthedocs.io>`_
    - [ ] `pathlib.Path <https://docs.python.org/3/library/pathlib.html>`_
    - [ ] `glob <https://docs.python.org/3/library/glob.html>`_
2. Integrations:
    - [x] `pandas <https://pandas.pydata.org>`_
    - [ ] `polars <https://pola-rs.github.io/polars-book/>`_
    - [ ] `pyarrow <https://arrow.apache.org/docs/python/>`_
    - [ ] `duckdb <https://duckdb.org>`_

---------------------------------------

.. toctree::
   :maxdepth: 2
   :caption: Introduction

   markdowns/quickstart
   markdowns/writing

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   markdowns/filesystem
   markdowns/cli

.. toctree::
   :maxdepth: 2
   :caption: Use Cases

   markdowns/collaboration
   markdowns/model_versioning

