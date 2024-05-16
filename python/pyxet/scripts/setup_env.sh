#!/bin/bash -ex

if [[ -z "$VIRTUAL_ENV" ]] ; then 

    if [[ ! -e pyproject.toml ]] ; then 
        echo "Run this script in the pyxet directory using ./scripts/$0"
        exit 1
    fi

    if [[ ! -e venv/ ]] ; then 
        echo "Setting up virtual environment."
        python -m venv venv
    
        source ./venv/bin/activate || ls -R ./ 

        pip install --upgrade pip
        pip install -r scripts/dev_requirements.txt
    else
        source ./venv/bin/activate
    fi


fi 
