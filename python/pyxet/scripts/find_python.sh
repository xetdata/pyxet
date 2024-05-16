#!/bin/bash -e

# To be sourced.  Sets PYTHON_EXECUTABLE

OS=$(uname -s)

if [[ "$1" == "release" ]] ; then 
    
    # In release mode, use the universal python executable on osx that ships with the system. However, 
    # this doesn't allow debugging, so don't do it for non-release mode
    if [[ "$OS" == "Darwin" ]]; then
        # Use system universal one
        echo "/usr/bin/python3"
    else
        if [[ "$(python --version)" == "Python 3"* ]] ; then
            echo "$(which python)"
        elif [[ "$(python3 --version)" == "Python 3"* ]] ; then
            echo "$(which python3)"
        else
            >&2 echo "Unable to find appropriate python version."
            exit 1
        fi
    fi
else
    if [[ ! -z $PYTHON_EXECUTABLE ]] ; then 
        echo "$PYTHON_EXECUTABLE"
    elif [[ "$(python --version)" == "Python 3"* ]] ; then
        echo "$(which python)"
    elif [[ "$(python3 --version)" == "Python 3"* ]] ; then
        echo "$(which python3)"
    else
        >&2 echo "Unable to find appropriate python version."
        exit 1
    fi

fi