# NOTE: **YOU ARE IN THE OBSOLETED BRANCH!** Everything here is old and is kept around for the purposes of documentation. Switch back to master if you're trying to run experiments and stuff!

# StrongBox (AKA/FKA: Buselfs) Experiments

This repository houses my energy/AES related experiments for the purposes of eventually developing a chacha-based device mapper utilizing poly1305 and LFS officially known
as [StrongBox](https://git.xunn.io/research/buselfs).

> Note that most of the executables in this project should probably be run as `root`. When it comes to the experiments, *definitely* run those as `root`!

## Structure

* `bin/` contains any compiled experiments and data crunching code
* `docs/` contains expansive documentation and detailed usage instructions
* `fb-personalities/` contains the filebench personalities used in earlier phases of the experiment
* `results/` contains all the results from running the experiment code, typically stored by category and then by datetime
* `vendor/` contains third-party and outside code that is not strictly under my control

## Files

### `cpp-X.c`

Call `make` in order to compile the `cpp-*` experiment scripts. You can then call them individually by name in `bin/` or run the entire current experiment by calling `make run`. You can test the `cpp-*` experiment scripts using `make test`. You can clear out `bin/` with `make clean`.

### `dataX.random`

These files are filled with random bits to be copied around during the various experiments (as a bare-bones replacement for dd). `X` represents the file size.

### `dd-read.sh` and `dd-write.sh`

These files are used by many of the experiment scripts to read and write data to the various filesystems for testing purposes. The old versions of these files are included for posterity's sake.

### `newagecmd.sh`

Latest quick commands and init procedures for the most recent StrongBox experiments.

### `python-X.py`

These are the old wattsup-based initial encryption experiments. They are rarely used.

### `rocked-X.py`

These scripts and executables are used for turning results (typically in the `results/` directory) into pretty graphs using plotly.

### `setupfilesystems.sh` and `teardownfilesystems.sh`

`setupfilesystems.sh` can be called without arguments and will setup the twelve filesystems used in the more recent experiments. `teardownfilesystems.sh` can be called without arguments and will completely undo whatever `setupfilesystems.sh` has done to the system.

### `setupramdisks.sh` and `teardownramdisks.sh`

`setupramdisks.sh` can be called without arguments and will setup a couple RAM disks. This is used for the older FDE vs NFDE experiments. `teardownramdisks.sh` can be called without arguments and will completely undo whatever `setupramdisks.sh` has done to the system.

### `storeresults.py`

`storeresults.sh` can be called without arguments and will take whatever result files are currently floating around in `results/` and put the in a subdir named with a timestamp. Note that results from experiment scripts are dumped unorganized into the `results/` directory.

### `testrunner.py`

Automation is king! This python script attempts to fully automate the "new age" latest StrongBox FDE experiments from initialization, setup, execution, and tear down.

