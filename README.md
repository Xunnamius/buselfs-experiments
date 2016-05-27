# Bernard's Energy-AES-1

This repository houses my energy/AES related experiments for the purposes of eventually developing a chacha-based LFS utilizing poly1305.

## Structure

* `bin/` contains any compiled experiments and data crunching code
* `docs` contains expansive documentation and detailed usage instructions
* `fb-personalities` contains the filebench personalities used in earlier phases of the experiment
* `results` contains all the results from running the experiment code
* `test` is a dummy directory that some of the experiments are allowed to write to for testing purposes
* `vendor` contains third-party and outside code that is not strictly under my control

## Files

* `dd-read.sh` and `dd-write.sh` are the scripts used by many of the experiment scripts to read and write data to the various filesystems for testing purposes
* The rocked-* scripts and executables are used for turning results (typically in the `results/` directory) into pretty graphs using plotly
* `storeresults.sh` can be called without arguments and will take whatever result files are currently floating around in `results/` and put the in a subdir named with a timestamp
* `setupramdisks.sh` can be called without arguments and will setup a couple RAM disks. This is used for the older FDE vs NFDE experiments
* `setupfilesystems.sh` can be called without arguments and will setup the twelve filesystems used in the more recent experiments
* `small.random` and `large.random` are files filled with random bits and are copied around during the lfs experiments

Call `make` in order to compile the cpp-* experimental scripts. You can then call them by name in `bin/`

**Note that most of these commands should probably be run as `root`. When it comes to the experiments, _definitely_ run those as `root`!**
