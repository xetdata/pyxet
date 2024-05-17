#!/bin/bash -ex

# Usage: in <repo>/python/pyxet/, run ./scripts/build_standalone_cli.sh
# Will build wheel in release mode, then build standalone executable using the xet packaged with the CLI

if [[ ! -e pyproject.toml ]] ; then 
    echo "Run this script in the pyxet directory using ./scripts/$0"
    exit 1
fi

source ./scripts/build_wheel.sh

pip install target/wheels/pyxet-*.whl

OS=$(uname -s)

# Build binary
if [[ "$OS" == "Darwin" ]]; then
    xet_cli_path="$(which xet)"
    echo "Path to xet = '${xet_cli_path}'"
    pyinstaller --onefile "$xet_cli_path" --target-arch universal2
elif [[ "$OS" == "Linux" ]] ; then
    xet_cli_path="$(which xet)"
    echo "Path to xet = '${xet_cli_path}'"
    pyinstaller --onefile "$xet_cli_path" 
else
    # Windows is weird.  Have to go directly to the cli path

    # Find the cli file, which isn't always where you want it to be. 
    xet_cli_path="./.venv_build/Lib/site-packages/pyxet/cli.py"
    echo "Path to xet = '${xet_cli_path}'"
    pyinstaller --onefile "$xet_cli_path" 
    mv dist/cli.exe dist/xet.exe
fi
