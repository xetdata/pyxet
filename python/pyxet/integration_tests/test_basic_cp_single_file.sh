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

# sync it up
xet cp data_1.bin $(xet_addr 1)/main/

# Now make sure this all matches up
check_repository_branch_and_local_directory_match data/ 1 main ./

# Then, make sure we can copy it all back correctly. 
xet cp $(xet_addr 1)/main/data_1.bin data_1_dup.bin
assert_files_equal data/data_1.bin data_1_dup.bin

# Make sure we can do copies within that repo
xet cp $(xet_addr 1)/main/data_1.bin $(xet_addr 1)/main/data_1_dup.bin
xet cp $(xet_addr 1)/main/data_1_dup.bin data_1_dup_2.bin
assert_files_equal data/data_1.bin data_1_dup_2.bin
