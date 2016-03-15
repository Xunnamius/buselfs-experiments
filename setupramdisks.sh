# Creates ram0 (nfde) and ram1 (fde)
sudo modprobe brd rd_nr=2 rd_size=524288
# badpasswordsarebad is the password
sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-random luksFormat /dev/ram1
sudo cryptsetup open --type luks /dev/ram1 fde
# Makes filesystems
sudo mkfs.ext4 /dev/mapper/fde
sudo mkfs.ext4 /dev/ram0
# Mounts those filesystems
sudo mount -t ext4 /dev/mapper/fde /media/fde-RAMDSK
sudo mount -t ext4 /dev/ram0 /media/nfde-RAMDSK
sudo -s
echo 0 > /proc/sys/kernel/randomize_va_space
exit