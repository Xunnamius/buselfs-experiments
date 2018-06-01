# The setup*.sh Scripts

These scripts are handy little creations that automate the setup process for various parts of the experiment.

## Expected Structure

The `setupfilesystems.sh` script expects the following directory structure to exist within `/home/odroid/bd3/fuse/mnt` beforehand:

```
mnt
├── 01-kext4-normal
│   └── write
├── 02-kext4-fuse-ext4
│   ├── fs.ext4
│   └── write (mount point for fs.ext4)
├── 03-kext4-fuse-ext4-dmc
│   ├── fs.ext4
│   └── write (mount pount for fs.ext4; contents only exist when fs.ext4 is mounted)
│       ├── fs.dmc
│       └── write (mount point for fs.dmc)
├── 04-kext4-dmc-fuse-ext4
│   ├── fs.dmc
│   └── write (contents only exist when fs.dmc is mounted)
│       ├── fs.ext4
│       └── write (mount point for fs.ext4)
├── 05-kext4-fuse-lfs
│   ├── fs.lfs
│   └── write (mount point for fs.ext4)
├── 06-kext4-fuse-lfs-chacha-poly
│   ├── fs.lfs
│   └── write (mount point for fs.ext4)
├── 07-rdext4-normal [symlink to /media/rd/07-rdext4-normal]
│   └── write
├── 08-rdext4-fuse-ext4 [symlink to /media/rd/08-rdext4-fuse-ext4]
│   ├── fs.ext4
│   └── write (mount point for fs.ext4)
├── 09-rdext4-fuse-ext4-dmc [symlink to /media/rd/09-rdext4-fuse-ext4-dmc]
│   ├── fs.ext4
│   └── write (mount point for fs.ext4; contents only exist when fs.ext4 is mounted)
│       ├── fs.dmc
│       └── write (mount point for fs.dmc)
├── 10-rdext4-dmc-fuse-ext4 [symlink to /media/rd/10-rdext4-dmc-fuse-ext4]
│   ├── fs.dmc
│   └── write (mount point for fs.ext4; contents only exist when fs.dmc is mounted)
│       ├── fs.ext4
│       └── write (mount point for fs.ext4)
├── 11-rdext4-fuse-lfs [symlink to /media/rd/11-rdext4-fuse-lfs]
│   ├── fs.lfs
│   └── write (mount point for fs.ext4)
└── 12-rdext4-fuse-lfs-chacha-poly [symlink to /media/rd/12-rdext4-fuse-lfs-chacha-poly]
│   ├── fs.lfs
│   └── write (mount point for fs.ext4)
```

## Specifications

Directories labeled `07-...` to `12-...` must be symlinks pointing to locations on `/media/rd`. Mount points are always and exclusively named `write`. Nothing should exist at the mount points unless filesystems have been mounted there.

`setupfilesystems.sh` will mount a ram disk to `/media/rd` and then create the structure for `07-...` to `12-...` and then mount everything that needs mounting for all twelve setups.

Note that, due to memory constraints, the sizes of the `07-...` to `12-...` filesystems is much smaller than their kext4 counterparts.
