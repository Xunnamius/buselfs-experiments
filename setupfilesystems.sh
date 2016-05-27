# If a ramdisk already exists where we want to make one, then fail out
if [ -b /dev/ram0 ]; then
    echo 'A ramdisk already exists at /dev/ram0!'
    echo 'Deallocate ramdisks with: sudo blockdev --flushbufs /dev/ramX'
    exit 1
fi

# # Creates ram0
# sudo modprobe brd rd_nr=1 rd_size=524288
# # badpasswordsarebad is the password
# sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-random luksFormat /dev/ram1
# sudo cryptsetup open --type luks /dev/ram1 fde
# # Makes filesystems
# sudo mkfs.ext4 /dev/mapper/fde
# sudo mkfs.ext4 /dev/ram0
# # Mounts those filesystems
# sudo mount -t ext4 /dev/mapper/fde /media/fde-RAMDSK
# sudo mount -t ext4 /dev/ram0 /media/nfde-RAMDSK
# sudo -s
# echo 0 > /proc/sys/kernel/randomize_va_space
exit
