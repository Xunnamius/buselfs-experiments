# StrongBox (AKA/FKA: Buselfs) Experiments

This repository houses my energy/AES related experiments for the purposes of ~~eventually~~ developing a cipher-swapping device mapper style log-structured file system utilizing poly1305 officially known as [StrongBox](https://git.xunn.io/research/buselfs).

> When something here needs to be executed, it should be executed as `root` (i.e. with `sudo`).

## Repository Structure

The structure of this repository is as follows:

### `bin/`

Any experiment that requires compilation will have said compilation yielded here. You can clear out this directory with `make clean`.

### `config/`

Any experimental configuration is stored in this directory. If you need to change, for example, where experiments are run you're probably looking for some setting that exists in this directory.

### `data/`

These files are filled with random bits to be copied around during the various experiments.

### `experiments/`

Call `make` in order to compile the `cpp-*` experiments. You can then call them individually by name in `bin/`. You can clear out `bin/` with `make clean`.

The testrunner-X.py scripts attempt to fully automate the latest StrongBox experiments from initialization through setup, execution, and tear down.

### `results/`

The scripts and executables in this directory are used for turning result files into pretty graphs using plotly.

`storeresults.sh` can be called without arguments and will take whatever result files are currently floating around in this directory and put them in a subdir named with a timestamp. Note that results from experiments are typically dumped unorganized into this directory.

The rest of the directories and files in this directory hold the results of running experiments. Check the README.md files for plotly visualizations.

### `vendor/`

These are third party files and repositories whose source is not under our control.
