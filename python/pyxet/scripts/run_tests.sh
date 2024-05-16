#!/bin/bash -ex

# Usage: in <repo>/python/pyxet/, run ./scripts/run_tests.sh. 
# Will build in development mode and run tests. 

if [[ ! -e pyproject.toml ]] ; then 
    echo "Run this script in the pyxet directory using ./scripts/$0"
    exit 1
fi

source ./scripts/setup_env.sh
activate_venv venv

# Clear out any old wheels
mkdir -p target/old_wheels/
mv target/wheels/* target/old_wheels/ || echo ""

# Install 
maturin build
pip install target/wheels/pyxet-*.whl

# This runs the tests in parallel using pytest-xdist
pytest -n 12 --verbose tests/
