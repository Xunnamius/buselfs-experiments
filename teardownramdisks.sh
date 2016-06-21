if ! [ -b /dev/ram0 ]; then
    echo '>>> A ramdisk does not exist at /dev/ram0!'
    echo '>>> Did you mean to run setupramdisks.sh ?'
    exit 1
fi

echo 'Enabling kernel virtual address space randomization for filebench'
sudo sh -c 'echo 1 > /proc/sys/kernel/randomize_va_space'

echo '>>> Unmounting /media/fde-RAMDSK'
sudo umount /media/fde-RAMDSK

echo '>>> Unmounting /media/nfde-RAMDSK'
sudo umount /media/nfde-RAMDSK

echo '>>> Unmounting faker.dmc'
sudo umount /home/odroid/bd3/fuse/mnt/01-kext4-normal/write/faker

echo '>>> Closing cryptsetups'
sudo cryptsetup close --type luks fde
sudo cryptsetup close --type luks faker.dmc

echo '>>> Destroying ram disks (hopefully)'
sudo blockdev --flushbufs /dev/ram0
sudo rm /dev/ram0
sudo blockdev --flushbufs /dev/ram1
sudo rm /dev/ram1
set -e
sudo rmmod brd

echo '>>> Done'
