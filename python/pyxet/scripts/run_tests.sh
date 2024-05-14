#!/bin/bash -ex

if [[ ! -e pyproject.toml ]] ; then 
    echo "Run this script in the pyxet directory using ./scripts/$0"
    exit 1
fi

source ./scripts/setup_env.sh

maturin develop

# This runs the tests in parallel using pytest-xdist
pytest -n 12 --verbose tests/
