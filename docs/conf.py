# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'pyxet'
copyright = '2023, xethub'
author = 'Jonathan Alexander'
release = '0.0.1a'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["myst_parser", "sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx.ext.viewcode", "sphinx_rtd_theme"]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'docs', '.venv']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_pydata_theme'
html_static_path = ['_static']

import os
import sys

sys.path.insert(0, os.path.abspath('../pyxet'))
