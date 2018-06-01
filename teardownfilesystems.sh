if ! [ -b /dev/ram0 ]; then
    echo '>>> A ramdisk does not exist at /dev/ram0!'
    echo '>>> Did you mean to run setupfilesystems.sh ?'
    exit 1
fi

echo '>>> Unmounting filesystem 01 (trivial)'

echo '>>> Unmounting filesystem 02'
sudo umount /home/odroid/bd3/fuse/mnt/02-kext4-fuse-ext4/write

echo '>>> Unmounting filesystem 03'
sudo umount /home/odroid/bd3/fuse/mnt/03-kext4-fuse-ext4-dmc/write/write
sudo cryptsetup close --type luks 03.fs.dmc
sudo umount /home/odroid/bd3/fuse/mnt/03-kext4-fuse-ext4-dmc/write

echo '>>> Unmounting filesystem 04'
sudo umount /home/odroid/bd3/fuse/mnt/04-kext4-dmc-fuse-ext4/write/write
sudo umount /home/odroid/bd3/fuse/mnt/04-kext4-dmc-fuse-ext4/write
sudo cryptsetup close --type luks 04.fs.dmc

echo '>>> Unmounting filesystem 05'
## todo

echo '>>> Unmounting filesystem 06'
## todo

echo '>>> Unmounting filesystem 07 (trivial)'

echo '>>> Unmounting filesystem 08'
sudo umount /media/rd/08-rdext4-fuse-ext4/write

echo '>>> Unmounting filesystem 09'
sudo umount /media/rd/09-rdext4-fuse-ext4-dmc/write/write
sudo cryptsetup close --type luks 09.fs.dmc
sudo umount /media/rd/09-rdext4-fuse-ext4-dmc/write

echo '>>> Unmounting filesystem 10'
sudo umount /media/rd/10-rdext4-dmc-fuse-ext4/write/write
sudo umount /media/rd/10-rdext4-dmc-fuse-ext4/write
sudo cryptsetup close --type luks 10.fs.dmc

echo '>>> Unmounting filesystem 11'
sudo fusermount -u /media/rd/11-rdext4-fuse-lfs/write
sudo rm -f /media/rd/11-rdext4-fuse-lfs/lfslog

echo '>>> Unmounting filesystem 12'
## todo

echo '>>> Destroying ram disk 0 (hopefully)'
sudo umount /media/rd
sudo blockdev --flushbufs /dev/ram0
sudo rm /dev/ram0
set -e
sudo rmmod brd

echo '>>> Done'
