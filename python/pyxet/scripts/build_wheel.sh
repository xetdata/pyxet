#!/bin/bash -ex

# Usage: in <repo>/python/pyxet/, run ./scripts/build_wheel.sh
# Will build wheel in release mode. 

if [[ ! -e pyproject.toml ]] ; then 
    echo "Run this script in the pyxet directory using ./scripts/$0"
    exit 1
fi

export MACOSX_DEPLOYMENT_TARGET=10.9
unset CONDA_PREFIX

rm -rf .venv_build
create_venv .venv_build release
activate_venv .venv_build

# Clear out any old wheels
mkdir -p target/old_wheels/
mv target/wheels/* target/old_wheels/ || echo ""

if [[ "$OS" == "Darwin" ]]; then
    maturin build --profile=cli-release --target=universal2-apple-darwin 
else 
    maturin build --profile=cli-release
fi

echo "Wheel is located at target/wheels/pyxet-*.whl"

