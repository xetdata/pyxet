#!/bin/bash -ex
export PS4='Line ${LINENO}: '
# Usage: in <repo>/python/pyxet/, run ./scripts/run_tests.sh. 
# Will build in development mode and run tests. 

if [[ ! -e pyproject.toml ]] ; then 
    echo "Run this script in the pyxet directory using ./scripts/$0"
    exit 1
fi

# Now use the dev environment for this.
source ./scripts/setup_env.sh
activate_dev_venv

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
pytest --verbose "../tests/"
