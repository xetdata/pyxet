#!/bin/bash -e 
# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Parse optional --temp-dir argument
for arg in "$@"; do
  case $arg in
    --test-dir=*)
      test_dir="${arg#*=}"
      shift # Remove --test-dir=<dir> from the arguments
      ;;
  esac
done

# Check for the correct number of arguments
if [ "$#" -ne 3 ]; then
    echo "Usage: [--test-dir=<dir>] <user> <repo1> <repo2>"
    exit 1
fi

# Set the environment variables of the remote repos
export _XET_TEST_USER="$1"
export _XET_TEST_REPO_1="$2"
export _XET_TEST_REPO_2="$3"

if [[ -z $test_dir ]] ; then 
  test_dir=$TMPDIR/xet_testing/
fi

>&2 echo "Running tests in directory $test_dir"
mkdir -p $test_dir

# Execute all files matching the pattern "test_*.sh", each in their own directory.
for file in "$DIR"/test_*.sh; do
    if [ -f "$file" ]; then

        # Extract the base name of the test without "test_" and ".sh"
        test_name=$(basename "$file" .sh | sed 's/^test_//')
        
        # Create a subdirectory named by the current date, time, and test name
        subdir=$(date "+%Y%m%d%H%M%S%N_${test_name}")
        mkdir -p "$test_dir/$subdir"
        
        # Change into that subdirectory
        cd "$test_dir/$subdir" || exit
        
        # Execute the test script inside that subdirectory
        XET_LOG_LEVEL=debug XET_LOG_PATH=`pwd`/xet_run.log bash "$file" && echo "$file: PASS" || echo "$file: ERROR"
        
        # Change back to the original directory
        cd - || exit
    fi
done

