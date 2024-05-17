#!/bin/bash -ex

venv_activate_script() {
    venv_name=$1
    
    unset CONDA_PREFIX

    if [[ ! -e "./$venv_name" ]] ; then
        >&2 create_venv $venv_name
    fi

    if [[ -e "./$venv_name/Scripts/activate" ]] ; then 
        echo "./$venv_name/Scripts/activate"
    else
        echo "./$venv_name/bin/activate"
    fi
}

create_venv() {

    venv_name=$1

    python_executable="$(./scripts/find_python.sh $2)"

    if [[ ! -e pyproject.toml ]] ; then 
        >&2 echo "Run this script in the pyxet directory using ./scripts/$0"
        exit 1
    fi

    if [[ ! -e ./$venv_name ]] ; then 
        >&2 echo "Setting up virtual environment."
        >&2 echo "Python version = $("$python_executable" --version)"
        >&2 "$python_executable" -m venv "./$venv_name"

        [[ -e "./$venv_name" ]] || exit 1 

        source $(venv_activate_script $venv_name)

        >&2 pip install --upgrade pip
        >&2 pip install -r scripts/dev_requirements.txt
    fi
}