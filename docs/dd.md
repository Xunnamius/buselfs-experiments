# WTF is DD?

`dd-read.sh` and `dd-write.sh` are the scripts used by many of the experiment scripts to read and write data to the various filesystems for testing purposes.

## Parameters

They both accept the same parameters:

* `writeto` is the absolute file path that DD will write to or read from
* `coretype` is the type of core you're using when writing (typically "big")
* `fstype` is the type of filesystem you're having dd write to

## Example usage

`./dd-write.sh test/testfile big testfs`

`./dd-read.sh test/testfile big testfs`

Note that these two scripts do drop the system page cache via `echo 1 | sudo tee /proc/sys/vm/drop_caches`. Further, they engage in direct IO via flags.
