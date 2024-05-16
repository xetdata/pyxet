#!/bin/bash

# Sets the current Cargo.toml to point to either the upstream libxet dependency, or a local path.

# Usage: ./set_libxet.sh [commit COMMIT | path PATH | restore | --help]

# Ensure Cargo.toml exists in the current directory
CARGO_FILE="Cargo.toml"
if [[ ! -f $CARGO_FILE ]]; then
    echo "$CARGO_FILE not found; please run in pyxet using ./scripts/$0"
    exit 1
fi

show_help() {
    echo "Usage: ./scripts/$0 [--commit COMMIT | --commit=COMMIT | --path PATH | --path=PATH | --restore | --help]"
    echo
    echo "Options:"
    echo "  commit COMMIT     Pin libxet to depend on remote commit COMMIT."
    echo "  path PATH         Pin libxet to depend on repository in path PATH."
    echo "  restore           Restore to default version depending on remote repo main."
    echo "  --help            Show this help message"
    exit 1
}

OPTION=""
VALUE=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        commit) OPTION="commit"; VALUE="$2"; shift 2 ;;
        path) OPTION="path"; VALUE="$2"; shift 2 ;;
        restore) OPTION="restore"; shift ;;
        --help) show_help; exit 0 ;;
        *) echo "Unknown parameter passed: $1"; show_help ;;
    esac
done

# Ensure an option is specified
if [[ -z "$OPTION" ]]; then
    show_help
fi

# Determine the replacement pattern based on the option
if [[ "$OPTION" == "commit" ]]; then
    if [[ -z "$VALUE" ]] ; then 
        show_help
    fi
    perl -0777 -i'' -pe 's|libxet = \{[^}]*features\s*=\s*\[([^\]]*)\][^}]*\}|libxet = { git = "https://github.com/xetdata/xet-core", features = [$1], rev = "'$VALUE'" }|gs' $CARGO_FILE
    echo "$CARGO_FILE set up to depend on libxet remote commit $VALUE"
    echo "Be sure to run ./scripts/$0 restore before committing changes."
elif [[ "$OPTION" == "path" ]]; then
    if [[ -z "$VALUE" ]] ; then 
        show_help
    fi
    ABS_PATH=$(realpath "$VALUE")
    if [[ -e "$ABS_PATH/libxet/Cargo.toml" ]] ; then 
        ABS_PATH="$ABS_PATH/libxet"
    fi

    if [[ ! -e "$ABS_PATH/Cargo.toml" ]] ; then 
        echo "libxet package not found at $(realpath "$VALUE")"
        exit 1
    fi

    perl -0777 -i'' -pe 's|libxet = \{[^}]*features\s*=\s*\[([^\]]*)\][^}]*\}|libxet = { path = "'$ABS_PATH'", features = [$1] }|gs' $CARGO_FILE
    echo "$CARGO_FILE set up to depend on libxet at local path $ABS_PATH" 
    echo "Be sure to run ./scripts/$0 restore before committing changes."
elif [[ "$OPTION" == "restore" ]]; then
    perl -0777 -i.bak -pe '
    s|libxet = \{[^}]*features\s*=\s*\[([^\]]*)\][^}]*\}|libxet = { git = "https://github.com/xetdata/xet-core", features = [$1] }|gs' $CARGO_FILE
    echo "$CARGO_FILE set up to depend on main on remote git repository."
fi
