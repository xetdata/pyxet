.. image:: images/logo.png

Welcome to pyxet's documentation!
=================================

pyxet is a Python library that provides a lightweight interface for the `XetHub <https://xethub.com/>`_  platform.

Installation
~~~~~~~~~~~~
Assuming you are on a supported OS (MacOS or Linux) and are using a supported version of Python (3.7+), set up your virtualenv with:

``python -m venv .venv``

``. .venv/bin/activate``

Then, install pyxet with:

``pip install pyxet``

Features
~~~~~~~~
1. A file-system like interface:
    - [x] `fsspec <https://filesystem-spec.readthedocs.io>`_
    - [x] `pathlib.Path <https://docs.python.org/3/library/pathlib.html>`_
    - [ ] `glob <https://docs.python.org/3/library/glob.html>`_
2. Integrations:
    - [x] `pandas <https://pandas.pydata.org>`_
    - [x] `polars <https://pola-rs.github.io/polars-book/>`_
    - [x] `pyarrow <https://arrow.apache.org/docs/python/>`_
    - [ ] `duckdb <https://duckdb.org>`_

.. toctree::
   :maxdepth: 2
   :caption: Introduction:

   markdowns/quickstart

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   markdowns/filesystem
   markdowns/integrations

.. toctree::
   :maxdepth: 2
   :caption: Use Cases:

   markdowns/collaboration
   markdowns/model_versioning

