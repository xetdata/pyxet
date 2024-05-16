#!/bin/bash -ex

# Usage: in <repo>/python/pyxet/, run ./scripts/build_wheel.sh
# Will build wheel in release mode. 

if [[ ! -e pyproject.toml ]] ; then 
    echo "Run this script in the pyxet directory using ./scripts/$0"
    exit 1
fi

export MACOSX_DEPLOYMENT_TARGET=10.9
unset CONDA_PREFIX

python_executable=$(./scripts/find_python.sh release)

# Clear out and rebuild the virtual env 
rm -rf .venv_build
$python_executable -m venv .venv_build
. .venv_build/bin/activate

pip install --upgrade pip
pip install -r scripts/dev_requirements.txt

# Clear out any old wheels
mkdir -p target/old_wheels/
mv target/wheels/* target/old_wheels/ || echo ""

if [[ "$OS" == "Darwin" ]]; then
    maturin build --profile=cli-release --target=universal2-apple-darwin 
else 
    maturin build --profile=cli-release
fi

echo "Wheel is located at target/wheels/pyxet-*.whl"

