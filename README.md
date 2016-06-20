# Bernard's Energy-AES-1

This repository houses my energy/AES related experiments for the purposes of eventually developing a chacha-based LFS utilizing poly1305.

## Structure

* `bin/` contains any compiled experiments and data crunching code
* `docs/` contains expansive documentation and detailed usage instructions
* `fb-personalities/` contains the filebench personalities used in earlier phases of the experiment
* `results/` contains all the results from running the experiment code, typically stored by category and then by datetime
* `test/` is a dummy directory that some of the experiments are allowed to write to for testing purposes
* `vendor/` contains third-party and outside code that is not strictly under my control

## Files

* `dd-read.sh` and `dd-write.sh` are the scripts used by many of the experiment scripts to read and write data to the various filesystems for testing purposes
* The rocked-* scripts and executables are used for turning results (typically in the `results/` directory) into pretty graphs using plotly
* `storeresults.sh` can be called without arguments and will take whatever result files are currently floating around in `results/` and put the in a subdir named with a timestamp. Note that results from experiment scripts are dumped unorganized into the `results/` directory.
* `setupramdisks.sh` can be called without arguments and will setup a couple RAM disks. This is used for the older FDE vs NFDE experiments
* `setupfilesystems.sh` can be called without arguments and will setup the twelve filesystems used in the more recent experiments
* `teardownramdisks.sh` can be called without arguments and will completely undo whatever `setupramdisks.sh` has done to the system
* `teardownfilesystems.sh` can be called without arguments and will completely undo whatever `setupfilesystems.sh` has done to the system
* `data.random` is a file filled with random bits to be copied around during the various experiments (as a bare-bones replacement for dd)

Call `make` in order to compile the cpp-* experiment scripts. You can then call them individually by name in `bin/` or run the entire current experiment by calling `make run`. You can test the cpp-* experiment scripts using `make test`. You can clear out `bin/` with `make clean`.

**Note that most of the executables in this project should probably be run as `root`. When it comes to the experiments, _definitely_ run those as `root`!**
