#!/usr/bin/env bash

set -e 
set -x

if [[ -z $_XET_TEST_USER ]] ; then 
  >&2 echo "environment variable XET_TEST_USER not set (set to remote user name)."
fi

if [[ -z $_XET_TEST_REPO_1 ]] ; then 
  >&2 echo "environment variable XET_TEST_REPO_1 not set (set to repository name of first testing remote; will be erased)."
fi

if [[ -z $_XET_TEST_REPO_2 ]] ; then 
  >&2 echo "environment variable XET_TEST_REPO_2 not set (set to repository name of second remote; (will be erased)."
fi

if [[ -z $XET_ENDPOINT ]] ; then 
  export XET_ENDPOINT="xethub.com"
fi

export _XET_REMOTE_1="https://$XET_ENDPOINT/$_XET_TEST_USER/$_XET_TEST_REPO_1"
export _XET_BASE_1="xet://$_XET_TEST_USER/$_XET_TEST_REPO_1/"
export _XET_REMOTE_2="https://$XET_ENDPOINT/$_XET_TEST_USER/$_XET_TEST_REPO_2"
export _XET_BASE_2="xet://$_XET_TEST_USER/$_XET_TEST_REPO_2/"

if [[ -z $_XET_TEST_DATA_DIR ]] ; then
  export _XET_TEST_DATA_DIR=$TMPDIR/xet_test_data
  >&2 echo "Using $_XET_TEST_DATA_DIR as data source."
  if [[ ! -e $_XET_TEST_DATA_DIR ]] ; then 
     mkdir -p $_XET_TEST_DATA_DIR
  fi

  if [[ ! -e $_XET_TEST_DATA_DIR/data.dat ]] ; then
    cat /dev/random | head -c 1024 > $_XET_TEST_DATA_DIR/data.dat
  fi
fi


>&2 echo "Using Repo 1 = $_XET_REMOTE_1" 
>&2 echo "Using Repo 2 = $_XET_REMOTE_2" 

# Takes 1 or 2 as argument
get_repo() {
  local index=$1
  local var_name="_XET_REMOTE_${index}"
  echo "${!var_name}"
}

xet_addr() {
  local index=$1
  local var_name="_XET_BASE_${index}"
  echo "${!var_name}"
}

# support both Mac OS and Linux for these scripts
if hash md5 2>/dev/null; then 
    checksum() {
        md5 -q $1
    }
else
    checksum() {
        md5sum $1 | head -c 32
    }
fi

die() { 
  >&2 echo "ERROR:>>>>> $1 <<<<<"
  exit 1
}

tmp_file_name () {
  h=$(cat /dev/random | head -c 100 | checksum | head -c 10)
  echo $1_$h
}

clean_repo() {

  local repo=$(get_repo $1)
  >&2 echo "Clearing repo $repo."

  local local_repo_dir=$(tmp_file_name repo_blank)/

  # Clean up the remote repo.
  # Reset the remote branch main to a single initial commit
  >&2 rm -rf $local_repo_dir 
  >&2 XET_LOG_LEVEL=debug XET_NO_SMUDGE=1 git clone -q $repo --branch main $local_repo_dir
  pushd $local_repo_dir

  # Delete all files, commit, push change. 
  git rm -rqf '*' && git commit -q -a -m "Cleared repository for testing." && git xet init && git push -q origin main

  # Delete all other branches
  >&2 remotes_to_del=$(git branch -r -l --format '%(refname)' | sed 's|refs/remotes/origin/||' | grep -v HEAD | grep -v main | grep -v notes || echo "")
  >&2 echo "Deleting remote branches $remotes_to_del" 

  if [[ ! -z $remotes_to_del ]] ; then 
    for branch in $remotes_to_del ; do 
      >&2 git push -q origin --delete $branch
    done
  fi

  >&2 popd # Back to original dir 

  >&2 rm -rf $local_repo_dir
}

check_directories_match() { 
  local dir_1="$1"  
  local dir_2="$2"

  set -x
  diff_report=$(rsync -r -f '- *.git*' -f '- .git/' --delete --dry-run --checksum --out-format="%f" "$dir_1/" "$dir_2/")

  if [[ ! -z $diff_report ]] ; then 
    >&2 echo "Directories $dir_1 and $dir_2 differ:"
    >&2 echo "OR: directories `pwd`/$dir_1 and `pwd`/$dir_2 differ:"
    >&2 echo $diff_report

    die "Directories $dir_1 and $dir_2 differ"
  fi
}

# Argument: local_dir <repo num> <branch> <end_directory>
check_repository_branch_and_local_directory_match() {
  local local_dir="$1"
  local repo=$(get_repo $2)
  local branch=$3
  local end_directory=$4

  >&2 echo "Verifying directories $local_dir and $repo/$branch/$end_directory are identical."

  local temp_dir=$(tmp_file_name check_$2_$branch)
  mkdir -p $temp_dir
  pushd $temp_dir
  
  >&2 XET_NO_SMUDGE=0 git xet clone $repo remote_$2/

  >&2 popd # Back to original dir 
  check_directories_match "$local_dir" "$temp_dir/remote_$2/$end_directory"
  
}


create_data_file() {
  local f="$1"
  local len_in_kb=$2

  mkdir -p "$(dirname $f)"
  dd if="$_XET_TEST_DATA_DIR/data.dat" of="$f" bs=1024 count="$(($len_in_kb - 1))"
  
  # Put a random block at the end to make sure the file is unique.
  cat /dev/random | head -c 1024 >> $f
  echo $(checksum $f)
}

assert_files_equal() {

  local h1=$(checksum $1)
  local h2=$(checksum $2)
  [[ $h1 == $h2 ]] || die "Assert Failed: Files $1 and $2 not equal."
}

assert_files_not_equal() {

  local h1=$(checksum $1)
  local h2=$(checksum $2)
  [[ $h1 != $h2 ]] || die "Assert Failed: Files $1 and $2 should not be equal."
}