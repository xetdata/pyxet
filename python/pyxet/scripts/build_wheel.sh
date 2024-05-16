#!/bin/bash -ex

# Usage: in <repo>/python/pyxet/, run ./scripts/build_wheel.sh
# Will build wheel in release mode. 

if [[ ! -e pyproject.toml ]] ; then 
    echo "Run this script in the pyxet directory using ./scripts/$0"
    exit 1
fi

export MACOSX_DEPLOYMENT_TARGET=10.9
unset CONDA_PREFIX

# Clear out the old virtual env.
rm -rf .venv_build

OS=$(uname -s)

if [[ -z "$PYTHON_EXECUTABLE" ]] ; then 
    if [[ "$OS" == "Darwin" ]]; then
        # Use system universal one
        PYTHON_EXECUTABLE=/usr/bin/python3
    else 
        PYTHON_EXECUTABLE=$(which python3)
    fi
fi

$PYTHON_EXECUTABLE -m venv .venv_build
. .venv_build/bin/activate

pip install --upgrade pip
pip install -r scripts/dev_requirements.txt

# Clear out any old wheels
mv target/wheels/ target/old_wheels/ || echo ""

if [[ "$OS" == "Darwin" ]]; then
    maturin build --profile=cli-release --target=universal2-apple-darwin 
else 
    maturin build --profile=cli-release
fi

echo "Wheel is located at target/wheels/pyxet-*.whl"

