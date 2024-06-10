#!/bin/bash -ex

_find_python () { 
    build_mode=$1
    
    if [[ "$build_mode" == "release" ]] ; then 
        
        # In release mode, use the universal python executable on osx that ships with the system. However, 
        # this doesn't allow debugging, so don't do it for non-release mode
        if [[ "$(uname -s)" == "Darwin" ]]; then
            # Use system universal one
            echo "/usr/bin/python3"
            return
        fi
    fi

    if [[ ! -z "$PYTHON_EXECUTABLE" ]] ; then 
        echo "$PYTHON_EXECUTABLE"
    elif [[ "$(python --version)" == "Python 3"* ]] ; then
        echo "$(which python)"
    elif [[ "$(python3 --version)" == "Python 3"* ]] ; then
        echo "$(which python3)"
    else
        >&2 echo "Unable to find appropriate python version."
        return 1
    fi
}

_venv_activate_script() {
    # Run this like 
    #
    #   source $(_venv_activate_script $venv_name)
    #
    # This is different on windows, so needs special casing. 
    venv_name=$1
    
    unset CONDA_PREFIX

    if [[ ! -e "./$venv_name" ]] ; then
        >&2 echo "venv '$venv_name' doesn't exist"
        exit 1
    fi

    if [[ -e "./$venv_name/Scripts/activate" ]] ; then 
        echo "./$venv_name/Scripts/activate"
    else
        echo "./$venv_name/bin/activate"
    fi
}

_setup_venv_packages () { 
    venv_name=$1
    build_mode=$2
   
    source $(_venv_activate_script $venv_name)

    # Make sure it's up to par and all the packages are correct. 
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


_init_venv() {

    venv_name=$1
    build_mode=$2

    python_executable="$(_find_python $build_mode)"

    if [[ ! -e ./$venv_name ]] ; then 
        >&2 echo "Setting up virtual environment."
        >&2 echo "Python version = $("$python_executable" --version)"
        >&2 "$python_executable" -m venv "./$venv_name"

        [[ -e "./$venv_name" ]] || exit 1 
    fi

    # Run this in a subprocess so as to not activate it here
    echo $(_setup_venv_packages "$venv_name" "$build_mode")
}


activate_release_venv() {
    venv_name=.venv_build

    if [[ ! -e pyproject.toml ]] ; then 
        >&2 echo "Run this in the pyxet directory."
        return 1
    fi
    
    # If we're already in a virtual env, then run with that 
    if [[ -z $_PYXET_BUILD_VIRTUAL_ENV ]] ; then
        
        # Use a new build environment that links against the system python on OSX 
        # and always creates a new environment.
        >&2 rm -rf $venv_name 
        >&2 _init_venv $venv_name release  
        >&2 source $(venv_activate_script $venv_name)
    else 
        >&2 source $(venv_activate_script ${_PYXET_BUILD_VIRTUAL_ENV})
    fi
    
    source $(venv_activate_script $venv_name)
    export _PYXET_BUILD_VIRTUAL_ENV=$venv_name
    export _PYXET_BUILD_MODE=release
}

activate_dev_venv() {
    venv_name=venv
    
    if [[ ! -e pyproject.toml ]] ; then 
        >&2 echo "Run this in the pyxet directory."
        return 1
    fi
    
    # If we're already in a virtual env, then don't worry about this. 
    if [[ -z $_PYXET_BUILD_VIRTUAL_ENV ]] ; then
        >&2 _init_venv $venv_name dev
        >&2 source $(venv_activate_script $venv_name)
    else 
        >&2 source $(venv_activate_script ${_PYXET_BUILD_VIRTUAL_ENV})
    fi
    export _PYXET_BUILD_VIRTUAL_ENV=$venv_name
    export _PYXET_BUILD_MODE=debug
}
