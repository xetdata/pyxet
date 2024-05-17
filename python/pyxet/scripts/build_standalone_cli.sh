#!/bin/bash -ex

# Usage: in <repo>/python/pyxet/, run ./scripts/build_standalone_cli.sh
# Will build wheel in release mode, then build standalone executable using the xet packaged with the CLI

if [[ ! -e pyproject.toml ]] ; then 
    echo "Run this script in the pyxet directory using ./scripts/$0"
    exit 1
fi

source ./scripts/build_wheel.sh

pip install target/wheels/pyxet-*.whl

# Find the binary, which isn't always where you want it to be. 
xet_path="$(which xet)"
if [[ -z "$(xet_path)" ]] ; then 
    echo "Error: Xet not found."
fi

if [[ ! -e "$(xet_path)" ]] ; then 
    # On windows, which strips the .exe
    if [[ -e "$(xet_path).exe" ]] ; then 
        xet_path="$(xet_path).exe"
    else
        where_attempt="$(where xet || echo '')"
        if [[ ! -z "$where_attempt" ]] && [[ -e "$where_attempt" ]] ; then 
            xet_path="$(where_attempt)"
        fi
    fi
fi

echo "Path to xet = '${xet_path}'"

# Build binary
if [[ "$OS" == "Darwin" ]]; then
    pyinstaller --onefile "$xet_path" --target-arch universal2
else 
    pyinstaller --onefile "$xet_path" 
fi
