#!/bin/bash -ex

# Usage: in <repo>/python/pyxet/, run ./scripts/build_wheel.sh
# Will build wheel in release mode. 

if [[ ! -e pyproject.toml ]] ; then 
    >&2 echo "Run this script in the pyxet directory using ./scripts/$0"
    exit 1
fi

OS=$(uname -s)

export MACOSX_DEPLOYMENT_TARGET=10.9
unset CONDA_PREFIX

# Adds in the install instructions.
>&2 source ./scripts/setup_env.sh

# Use a new build environment that links against the system python on OSX 
# and always creates a new environment.

# If we're already in a virtual env, then don't worry about this. 
if [[ -z $_PYXET_BUILD_VIRTUAL_ENV ]] ; then
    >&2 rm -rf .venv_build
    >&2 create_venv .venv_build release  
    >&2 source $(venv_activate_script .venv_build)
else 
    >&2 source $(venv_activate_script ${_PYXET_BUILD_VIRTUAL_ENV})
fi

# Clear out any old wheels
>&2 mkdir -p target/old_wheels/
>&2 mv target/wheels/* target/old_wheels/ || echo ""

# Mode
if [[ $_PYXET_BUILD_MODE == "debug" ]] ; then 
    flags=
else
    flags="--profile=cli-release"

    if [[ "$OS" == "Darwin" ]]; then
        flags="$flags --target=universal2-apple-darwin"
    fi
fi

>&2 maturin build $flags 

wheel=$(ls ./target/wheels/pyxet-*.whl | head -n 1)
>&2 echo "Wheel is located at $wheel"
echo $wheel

