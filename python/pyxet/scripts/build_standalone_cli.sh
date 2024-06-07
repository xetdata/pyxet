#!/bin/bash -ex

# Usage: in <repo>/python/pyxet/, run ./scripts/build_standalone_cli.sh
# Will build wheel in release mode, then build standalone executable using the xet packaged with the CLI

if [[ ! -e pyproject.toml ]] ; then 
    >&2 echo "Run this script in the pyxet directory using ./scripts/$0"
    exit 1
fi

>&2 wheel_location=$(./scripts/build_wheel.sh)

>&2 pip install $wheel_location 
>&2 pip install -r ./scripts/cli_requirements.txt 

OS=$(uname -s)

xet_cli_path="./scripts/xet_standalone_entry.py"
>&2 echo "Path to xet entry script = '${xet_cli_path}'"

# Build binary
if [[ "$OS" == "Darwin" ]]; then
    if [[ ${_PYXET_BUILD_MODE} == "debug" ]] ; then 
        target_flag=
    else
        target_flag="--target-arch=universal2" 
    fi

    >&2 pyinstaller --onefile "$xet_cli_path" --name xet $target_flag
    cli_path="dist/xet"
elif [[ "$OS" == "Linux" ]] ; then
    >&2 pyinstaller --onefile "$xet_cli_path" --name xet
    cli_path="dist/xet"
else
    >&2 pyinstaller --onefile "$xet_cli_path" --name xet
    cli_path="dist/xet.exe"
fi

>&2 echo "Standalone installer is located at ${cli_path}."
echo ${cli_path} 
