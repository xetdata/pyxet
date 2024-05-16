#!/bin/bash -ex

activate_venv() {
    venv_name=$1
    
    unset CONDA_PREFIX

    if [[ ! -e "./$venv_name" ]] ; then
        create_venv $venv_name
    fi

    if [[ -e "./$venv_name/Scripts/activate" ]] ; then 
        echo "Activating virtual env ./$venv_name using script."
        source "./$venv_name/Scripts/activate"
    else
        echo "Activating virtual env ./$venv_name."
        source "./$venv_name/bin/activate"
    fi
}

create_venv() {
    if [[ -z "$VIRTUAL_ENV" ]] ; then 
        venv_name=$1

        python_executable=$(./scripts/find_python.sh $2)

        if [[ ! -e pyproject.toml ]] ; then 
            echo "Run this script in the pyxet directory using ./scripts/$0"
            exit 1
        fi

        if [[ ! -e ./$venv_name ]] ; then 
            echo "Setting up virtual environment."
            echo "Python version = $($python_executable--version)"
            $python_executable -m venv ./$venv_name

            [[ -e "./$venv_name" ]] || exit 1 

            activate_venv $venv_name 

            pip install --upgrade pip
            pip install -r scripts/dev_requirements.txt
        else
            activate_venv $venv_name 
        fi
    fi 
}