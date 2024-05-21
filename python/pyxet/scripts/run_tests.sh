#!/bin/bash -ex
export PS4='Line ${LINENO}: '
# Usage: in <repo>/python/pyxet/, run ./scripts/run_tests.sh. 
# Will build in development mode and run tests. 

if [[ ! -e pyproject.toml ]] ; then 
    echo "Run this script in the pyxet directory using ./scripts/$0"
    exit 1
fi

source ./scripts/setup_env.sh
create_venv venv dev
source $(venv_activate_script venv)

if [[ -z "$VIRTUAL_ENV" ]] ; then 
  echo "Failed to activate virtual env."
  exit 1
fi


# Clear out any old wheels
mkdir -p target/old_wheels/
mv target/wheels/* target/old_wheels/ || echo ""

echo "$(which pip)"

# Install 
maturin build
pip install target/wheels/pyxet-*.whl

# TODO: This runs the tests in parallel using pytest-xdist
# Error: tests in cli can't be run simultaneously actually, as there are conflicts.
#pytest -n 12 --verbose tests/
pytest --verbose tests/

