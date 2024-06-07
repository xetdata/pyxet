#!/bin/bash -ex
export PS4='Line ${LINENO}: '
# Usage: in <repo>/python/pyxet/, run ./scripts/run_tests.sh. 
# Will build in development mode and run tests. 

if [[ ! -e pyproject.toml ]] ; then 
    echo "Run this script in the pyxet directory using ./scripts/$0"
    exit 1
fi

source ./scripts/setup_env.sh
create_venv venv dev  # The dev part here installs the additional dev requirements
source $(venv_activate_script venv)

export _PYXET_BUILD_MODE=debug
export _PYXET_BUILD_VIRTUAL_ENV=venv

# Build the wheel.
wheel=$(./scripts/build_wheel.sh)

# Build the standalone cli and wheel 
cli=$(./scripts/build_standalone_cli.sh)

# Install the wheel
pip install "$wheel"

if [[ -z "$VIRTUAL_ENV" ]] ; then 
  echo "Failed to activate virtual env."
  exit 1
fi

# Make sure windows executable can run anywhere 
work_dir=./.testing_tmp
rm -rf $work_dir || echo ""
mkdir -p $work_dir

cp "$cli" "$work_dir"
cd "$work_dir"

export XET_STANDALONE_CLI="./$(basename ${cli})"
pytest -n 12 --verbose "../tests/"
