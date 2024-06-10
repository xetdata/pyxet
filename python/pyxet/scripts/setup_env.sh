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
    build_mode=$2

    python_executable="$(./scripts/find_python.sh $build_mode)"

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
        export _PYXET_BUILD_VIRTUAL_ENV=$venv_name
    fi
    
    # Make sure it's up to par. 
    >&2 pip install --upgrade pip
    if [[ $build_mode == "release" ]] ; then 
        if [[ "$(uname -s)" == "Darwin" ]]; then
            # This is VERY annoying.  If a platform specific wheel is published, then that is sometimes prefered by pip over the universal2 wheel, which causes problems.
            mkdir -p $venv_name/packages
            pushd $venv_name/packages
            # pip install doesn't allow you to use the --platform= flag. So you have to download it and then install those wheels manually.
            pip download --only-binary=:all: --platform=macosx_10_9_universal2 --platform=macosx_11_0_universal2 -r ../../scripts/build_requirements.txt
            pip install *.whl
            popd
        fi
        
        # For building the wheel / standalone xet, use minimal installation
        # environment; otherwise may pull in non-universal2 compatible package.
        >&2 pip install --upgrade -r scripts/build_requirements.txt
    else
        # Install both.
        >&2 pip install --upgrade -r scripts/build_requirements.txt
        >&2 pip install --upgrade -r scripts/dev_requirements.txt
    fi
}


create_release_venv() {

    # If we're already in a virtual env, then don't worry about this. 
    if [[ -z $_PYXET_BUILD_VIRTUAL_ENV ]] ; then
        
        # Use a new build environment that links against the system python on OSX 
        # and always creates a new environment.
        >&2 rm -rf .venv_build
        >&2 create_venv .venv_build release  
        >&2 source $(venv_activate_script .venv_build)
    else 
        >&2 source $(venv_activate_script ${_PYXET_BUILD_VIRTUAL_ENV})
    fi
}
