set -e

# If a ramdisk already exists where we want to make one, then fail out
if [ -b /dev/ram0 ] || [ -b /dev/ram1 ] ; then
    echo 'A ramdisk already exists at /dev/ram0 and/or /dev/ram1!'
    echo 'Deallocate ramdisks with `sudo blockdev --flushbufs /dev/ramX` followed by `sudo rm /dev/ramX` and `sudo rmmod brd`'
    exit 1
fi

# Creates ram0 (nfde) and ram1 (fde)
echo 'Creating (2) ram disks of size 512MB each'
sudo modprobe brd rd_nr=2 rd_size=524288

# badpasswordsarebad is the password
echo 'Setting up AES-XTS (use password: badpasswordsarebad)'
sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-random luksFormat /dev/ram1
sudo cryptsetup open --type luks /dev/ram1 fde
sudo cryptsetup open --type luks /home/odroid/bd3/fuse/mnt/01-kext4-normal/fs.dmc faker.dmc

# Makes filesystems
echo 'Making the filesystems'
sudo mkfs.ext4 /dev/mapper/fde
sudo mkfs.ext4 /dev/ram0

# Mounts those filesystems
echo 'Mounting the filesystems'
sudo mount -t ext4 /dev/mapper/fde /media/fde-RAMDSK
sudo mount -t ext4 /dev/ram0 /media/nfde-RAMDSK
sudo mount -t ext4 /dev/mapper/faker.dmc /home/odroid/bd3/fuse/mnt/01-kext4-normal/write/faker

echo 'Disabling kernel virtual address space randomization for filebench'
sudo sh -c 'echo 0 > /proc/sys/kernel/randomize_va_space'

echo 'Done'
