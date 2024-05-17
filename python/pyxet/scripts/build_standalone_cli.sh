#!/bin/bash -ex

# Usage: in <repo>/python/pyxet/, run ./scripts/build_standalone_cli.sh
# Will build wheel in release mode, then build standalone executable using the xet packaged with the CLI

if [[ ! -e pyproject.toml ]] ; then 
    echo "Run this script in the pyxet directory using ./scripts/$0"
    exit 1
fi

source ./scripts/build_wheel.sh

pip install target/wheels/pyxet-*.whl

# Find the cli file, which isn't always where you want it to be. 
xet_cli_path="./.venv_build/lib/site-packages/pyxet/cli.py"

echo "Path to xet = '${xet_cli_path}'"

# Build binary
if [[ "$OS" == "Darwin" ]]; then
    pyinstaller --onefile "$xet_cli_path" --target-arch universal2
else 
    pyinstaller --onefile "$xet_cli_path" 
fi
