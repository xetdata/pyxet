# Source this file to get going on development.

bash -e ./scripts/setup_env.sh

source venv/bin/activate
export MACOSX_DEPLOYMENT_TARGET=10.9
unset CONDA_PREFIX
