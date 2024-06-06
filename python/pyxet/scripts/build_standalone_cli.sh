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

xet_cli_path="./scripts/xet_standalone_entry.py"
echo "Path to xet entry script = '${xet_cli_path}'"

# Build binary
if [[ "$OS" == "Darwin" ]]; then
    pyinstaller --onefile "$xet_cli_path" --name xet --target-arch universal2 
elif [[ "$OS" == "Linux" ]] ; then
    pyinstaller --onefile "$xet_cli_path" --name xet
else
    pyinstaller --onefile "$xet_cli_path" --name xet
fi
