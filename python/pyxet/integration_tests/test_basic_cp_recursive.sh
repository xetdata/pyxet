#!/bin/bash -e

# Set up the tests. 
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
. $DIR/setup.sh


# Clear out the testing remote
clean_repo 1

# Make the local dir
mkdir -p data/

# Add in a few  data files
create_data_file data/data_1.bin 1024
create_data_file data/data_2.bin 512
create_data_file data/subdir/data_3.bin 100

# sync it up
xet cp -r data/ $(xet_addr 1)/main/data/

# Now make sure this all matches up
check_repository_branch_and_local_directory_match data/ 1 main data/

# Then, make sure we can copy it all back correctly. 
xet cp -r $(xet_addr 1)/main/data/ data_2/
check_directories_match data/ data_2/

# Make sure we can do copies within that repo
xet cp -r $(xet_addr 1)/main/data/ $(xet_addr 1)/main/data_dup/
check_repository_branch_and_local_directory_match data/ 1 main data_dup/