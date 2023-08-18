PyXet Integration tests. 

To run these tests, you need two blank repos that will be cleared and used for testing. 

To run all the tests, do 

./run_tests.sh --test-dir=test_dir/ <xet user> <repo1> <repo2> 

This script will run all the tests, running each one in a directory in the test_dir
for later analysis if needed.  

Any bash script that starts with test_ is considered a test.  It should first 
source the setup.sh file to get all the correct functions. 

See other tests for examples. 



