set -e

# If a ramdisk already exists where we want to make one, then fail out
if [ -b /dev/ram0 ]; then
    echo '>>> A ramdisk already exists at /dev/ram0!'
    echo '>>> Deallocate ramdisks with: `sudo blockdev --flushbufs /dev/ramX` followed by `sudo rm /dev/ramX`'
    exit 1
fi

# Creates ram0
echo '>>> Creating (1) ram disk of size 512MB'
sudo modprobe brd rd_nr=1 rd_size=524288

echo '>>> Making a filesystem atop the ram disk'
sudo mkfs.ext4 /dev/ram0

echo '>>> Mounting to /media/rd'
sudo mount -t ext4 /dev/ram0 /media/rd

echo '>>> Setting up and mounting (trivial) directory structure 07 on ram disk'
sudo mkdir -p /media/rd/07-rdext4-normal/write

echo '>>> Setting up and mounting directory structure 08 on ram disk'
sudo mkdir -p /media/rd/08-rdext4-fuse-ext4/write
sudo dd if=/dev/zero of=/media/rd/08-rdext4-fuse-ext4/fs.ext4 bs=64M count=1
sudo mkfs.ext4 /media/rd/08-rdext4-fuse-ext4/fs.ext4
sudo fuse-ext2 /media/rd/08-rdext4-fuse-ext4/fs.ext4 /media/rd/08-rdext4-fuse-ext4/write -o rw+

echo '>>> Setting up and mounting directory structure 09 on ram disk'
sudo mkdir -p /media/rd/09-rdext4-fuse-ext4-dmc/write
sudo dd if=/dev/zero of=/media/rd/09-rdext4-fuse-ext4-dmc/fs.ext4 bs=80M count=1
sudo mkfs.ext4 /media/rd/09-rdext4-fuse-ext4-dmc/fs.ext4
sudo fuse-ext2 /media/rd/09-rdext4-fuse-ext4-dmc/fs.ext4 /media/rd/09-rdext4-fuse-ext4-dmc/write -o rw+
sudo mkdir /media/rd/09-rdext4-fuse-ext4-dmc/write/write
sudo dd if=/dev/zero of=/media/rd/09-rdext4-fuse-ext4-dmc/write/fs.dmc bs=64M count=1
# badpasswordsarebad is the password
sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-random luksFormat /media/rd/09-rdext4-fuse-ext4-dmc/write/fs.dmc
sudo cryptsetup open --type luks /media/rd/09-rdext4-fuse-ext4-dmc/write/fs.dmc 09.fs.dmc
sudo mkfs.ext4 /dev/mapper/09.fs.dmc
sudo mount -t ext4 /dev/mapper/09.fs.dmc /media/rd/09-rdext4-fuse-ext4-dmc/write/write

echo '>>> Setting up and mounting directory structure 10 on ram disk'
sudo mkdir -p /media/rd/10-rdext4-dmc-fuse-ext4/write
sudo dd if=/dev/zero of=/media/rd/10-rdext4-dmc-fuse-ext4/fs.dmc bs=80M count=1
# badpasswordsarebad is the password
sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-random luksFormat /media/rd/10-rdext4-dmc-fuse-ext4/fs.dmc
sudo cryptsetup open --type luks /media/rd/10-rdext4-dmc-fuse-ext4/fs.dmc 10.fs.dmc
sudo mkfs.ext4 /dev/mapper/10.fs.dmc
sudo mount -t ext4 /dev/mapper/10.fs.dmc /media/rd/10-rdext4-dmc-fuse-ext4/write
sudo mkdir /media/rd/10-rdext4-dmc-fuse-ext4/write/write
sudo dd if=/dev/zero of=/media/rd/10-rdext4-dmc-fuse-ext4/write/fs.ext4 bs=64M count=1
sudo mkfs.ext4 /media/rd/10-rdext4-dmc-fuse-ext4/write/fs.ext4
sudo fuse-ext2 /media/rd/10-rdext4-dmc-fuse-ext4/write/fs.ext4 /media/rd/10-rdext4-dmc-fuse-ext4/write/write -o rw+

echo '>>> Setting up and mounting directory structure 11 on ram disk'
sudo mkdir -p /media/rd/11-rdext4-fuse-lfs/write
cd /media/rd/11-rdext4-fuse-lfs
sudo sh -c "vendor/github/lfs/lfs /media/rd/11-rdext4-fuse-lfs/write"
cd -

echo '>>> Setting up and mounting directory structure 12 on ram disk'
sudo mkdir -p /media/rd/12-rdext4-fuse-lfs-chacha-poly/write
## todo

echo '>>> Setting up and mounting directory structure 13 on ram disk'
sudo mkdir -p /media/rd/13-rdext4-fuse-lfs-AES-GCM/write
## todo

echo '>>> Mounting filesystem 01 (trivial)'

echo '>>> Mounting filesystem 02'
sudo fuse-ext2 /home/odroid/bd3/fuse/mnt/02-kext4-fuse-ext4/fs.ext4 /home/odroid/bd3/fuse/mnt/02-kext4-fuse-ext4/write -o rw+

echo '>>> Mounting filesystem 03'
sudo fuse-ext2 /home/odroid/bd3/fuse/mnt/03-kext4-fuse-ext4-dmc/fs.ext4 /home/odroid/bd3/fuse/mnt/03-kext4-fuse-ext4-dmc/write -o rw+
sudo cryptsetup open --type luks /home/odroid/bd3/fuse/mnt/03-kext4-fuse-ext4-dmc/write/fs.dmc 03.fs.dmc
sudo mount -t ext4 /dev/mapper/03.fs.dmc /home/odroid/bd3/fuse/mnt/03-kext4-fuse-ext4-dmc/write/write

echo '>>> Mounting filesystem 04'
sudo cryptsetup open --type luks /home/odroid/bd3/fuse/mnt/04-kext4-dmc-fuse-ext4/fs.dmc 04.fs.dmc
sudo mount -t ext4 /dev/mapper/04.fs.dmc /home/odroid/bd3/fuse/mnt/04-kext4-dmc-fuse-ext4/write
sudo fuse-ext2 /home/odroid/bd3/fuse/mnt/04-kext4-dmc-fuse-ext4/write/fs.ext4 /home/odroid/bd3/fuse/mnt/04-kext4-dmc-fuse-ext4/write/write -o rw+

echo '>>> Mounting filesystem 05'
## todo

echo '>>> Mounting filesystem 06'
## todo

echo '>>> Done'
