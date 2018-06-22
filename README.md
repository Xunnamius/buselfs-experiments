# StrongBox (AKA/FKA: Buselfs) Experiments

This repository houses my energy/AES related experiments for the purposes of ~~eventually~~ developing a cipher-swapping device mapper style log-structured file system utilizing poly1305 officially known as [StrongBox](https://git.xunn.io/research/buselfs).

> When something here needs to be executed, it should be executed as `root` (i.e. with `sudo`).

## Repository Structure

The structure of this repository is as follows:

### `bin/`

Any experiment that requires compilation will have said compilation yielded here. You can clear out this directory with `make clean`.

### `config/`

Any experimental configuration is stored in this directory. If you need to change, for example, where experiments are run then you're probably looking for some setting that exists in this directory.

### `data/`

These files are filled with random bits to be copied around during the various experiments.

### `experiments/`

Call `make` in order to compile the `*.c` experiments. You can then call them individually by name in `bin/`. You can clear out `bin/` with `make clean`.

The testrunner-X.py scripts attempt to fully automate the latest StrongBox experiments from initialization through setup, execution, and tear down.

The `../initrunner.py` script just lays the groundwork for eventual environment initialization/test running by the other experiments. You can call this manually to test your setup and verify your [vars.mk](config/vars.mk-dist) is being interpreted properly, but it is not mandatory and will be called automatically by the testrunner-X scripts (it's idempotent).

### `results/`

The scripts and executables in this directory are used for turning result files into pretty graphs using plotly.

`storeresults.sh` can be called without arguments and will take whatever result files are currently floating around in this directory and put them in a subdir named with a timestamp. Note that results from experiments are typically dumped unorganized into this directory.

The rest of the directories and files in this directory hold the results of running experiments. Check the README.md files for plotly visualizations.

### `vendor/`

These are third party files and repositories whose source is not under our control.

## A Big Shiny Glass Box That Reads: "Break In Case of Fire!"

### LINUX EMERGENCY SHUTDOWN

```bash
sudo -s
echo 1 > /proc/sys/kernel/sysrq
echo b > /proc/sysrq-trigger
```

### BRIM FILLER

```bash
sudo dd if=/dev/zero of=XXX/filler bs=1M count=750
```

## How To Initialize Odroids

For Odroids outside of U of C, where permission separation and other concerns are not an issue, the italicized commands can be massaged into more standard/less annoying alternatives. Also, see [vars.mk](config/vars.mk-dist) to customize the experiment suite, including overriding the default locations of the repositories below.

1. `sudo apt update && sudo apt upgrade`
2. (maybe do the following, potentially dangerous) `sudo apt full-upgrade`
3. `sudo apt install build-essential nilfs-tools f2fs-tools cryptsetup ruby xclip python3-pexpect python3-pip ne keyring debian-keyring`
4. Compile NBD, NILFS2, and F2FS modules if they are not available via `modprobe`
    1. `git clone https://github.com/hardkernel/linux hardkernel-linux`
    2. `cd hardkernel-linux`
    3. `apt install linux-headers-$(uname -r)`
    4. Search [hardkernel releases](https://github.com/hardkernel/linux/releases) for your `uname -r` and `git checkout {hash}` the hardkernel-linux repo with whatever commit SHA hash points to that release (GitHub tells you the hash).
    5. `cp /usr/src/linux-headers-$(uname -r)/Module.symvers .`
    6. `make oldconfig`
    7. Use `ne .config` to enable (by adding `=m`) any extra modules
    8. `make prepare`
        * *maybe `make odroidxu4_defconfig` as well; only run it if things aren't working [[hint?]](https://wiki.odroid.com/odroid-xu4/software/building_kernel#y)*
    9. `make modules_prepare`
    10. `make SUBDIRS=scripts/mod`
    11. `make SUBDIRS=relative/path/to/where/module/lives modules`
    12. `sudo cp {relative-path-to-where-module-lives}/{module}.ko /lib/modules/{kernel}/kernel/{relative-path-to-where-module-lives}/`
    13. `sudo depmod`
    14. `sudo modprobe {module}`
5. Copy over `~/.ssh` (you may also have to configure the OpenSSH server @ `/etc/ssh/sshd_config` and `~/.ssh/authorized_keys`)
5. *Copy over `~/marshaller`*
6. *Copy over `~/.bash_aliases`*
7. *`mkdir -p ~/bd3/repos`*
8. *Copy [these aliases](https://git.xunn.io/snippets/4) into `~/bd3/.bash_aliases`*
9. Git clone relevant repositories (below) into `~/bd3/repos` or some location of your choice if you're not using the custom `~./bash_aliases`
    - [Forked BUSE repository](https://github.com/Xunnamius/BUSE) **(required)**
    - [Early BUSE constructions reliant on FUSE and `losetup`](https://git.xunn.io/research/buse-fuse-losetup)
    - [StrongBox (Buselfs)](https://git.xunn.io/research/buselfs) **(required)**
    - [The StrongBox suite of experiments (this repository)](https://git.xunn.io/research/buselfs-experiments) **(required)**
    - [Energymon repository for installing energymon](https://github.com/energymon/energymon)
10. Copy [vars.mk-dist](config/vars.mk-dist) to [vars.mk](config/vars.mk-dist) and modify the settings to your liking

### Test Odroid Initialization

Not an exhaustive test, but it will catch most of the more glaring oversights:

```bash
sudo ./initrunner.py
```
