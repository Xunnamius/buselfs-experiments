# StrongBox (AKA: Buselfs) Documentation

We have come a long way...

## Experimental Progression

```
(2015) shmoo+Filebench "timed" experiments
            |
            V
(2015) shmoo+Filebench "freerun" experiments
            |
            V
(2016) shmoo+dd "freerun" FDE/NFDE experiments
            |
            V
(2016) dd lfs/chacha experiments
            |
            V
(2017) ramdisk/filesystems experiments (setup/teardown)
            |
            V
(2017) newagecmd + semi-automatic testrunner experiment suite
            |
            V
(2018) fully-automatic testrunner-X experiment suites
            |
            V
    (whatever is next!)
```

## Current Usage

To run the current fully automated experiment suite (from this repository's
root):

```bash
sudo ./testrunner.py
```

If you're making a new instance of the `Librunner` class, note that you can
setup `librunnerInstance.verbose = False` to make the library shut up while
you're using it (`Librunner::verbose` is `true` by default).

If you want `Librunner` to log output to a file as it goes along, set
`librunnerInstance.logFile` to some sort of file object or stream. It will
be passed to `print()` as an argument to the `file=` parameter.

For example:

```python
with open('myfile.txt', 'w') as f:
    librunnerInstance.logFile = f
    ...
```

Of course, be careful not to have your `Librunner` instance use a file handler
that has been closed (i.e. `f.close()`).

## Current experiments

Testrunner automates the following experiments (in order):

- one
- two
- three
- four
- five
