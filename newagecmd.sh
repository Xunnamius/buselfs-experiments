
# INIT (run once)
sudo modprobe nbd
sudo modprobe logfs
sudo modprobe nilfs2
sudo modprobe f2fs

mkdir /tmp/ram0 /tmp/nbd0 /tmp/nbd1 /tmp/nbd2 /tmp/nbd3 /tmp/nbd4 /tmp/nbd5 /tmp/nbd6 /tmp/nbd7 /tmp/nbd8 /tmp/nbd9 /tmp/nbd10 /tmp/nbd11 /tmp/nbd12 /tmp/nbd13 /tmp/nbd14 /tmp/nbd15


sudo modprobe brd rd_nr=1 rd_size=1048576
sudo mkfs.ext4 /dev/ram0
sudo mount -t ext4 /dev/ram0 /tmp/ram0

######################################

##### BUSE+NILFS2

sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd0 2> ~/bd3/debug-nbd0.debug-log &
sudo mkfs -t nilfs2 /dev/nbd0
sudo mount -t nilfs2 /dev/nbd0 /tmp/nbd0
mount

sudo bin/cpp-simple-freerun big ramdisk+buse+nilfs2 /tmp/nbd0

# CLEANUP

sudo umount /tmp/nbd0

# Now close buselfs!

##### BUSE+F2FS

sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd1 2> ~/bd3/debug-nbd1.debug-log &
sudo mkfs -t f2fs /dev/nbd1
sudo mount -t f2fs /dev/nbd1 /tmp/nbd1
mount

sudo bin/cpp-simple-freerun big ramdisk+buse+f2fs /tmp/nbd1

# CLEANUP

sudo umount /tmp/nbd1

# Now close buselfs!

# BUSE+LOGFS

sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd2 2> ~/bd3/debug-nbd2.debug-log &
sudo mkfs -t logfs /dev/nbd2
# CONFIRM
sudo mount -t logfs /dev/nbd2 /tmp/nbd2
mount

sudo bin/cpp-simple-freerun big ramdisk+buse+logfs /tmp/nbd2

# CLEANUP

sudo umount /tmp/nbd2

# Now close buselfs!

# BUSE+EXT4OJ

sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd3 2> ~/bd3/debug-nbd3.debug-log &
sudo mkfs -t ext4 /dev/nbd3
sudo mount -t ext4 /dev/nbd3 /tmp/nbd3
mount

sudo bin/cpp-simple-freerun big ramdisk+buse+ext4-oj /tmp/nbd3

# CLEANUP

sudo umount /tmp/nbd3

# Now close buselfs!

# BUSE+EXT4FJ

sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd4 2> ~/bd3/debug-nbd4.debug-log &
sudo mkfs -t ext4 /dev/nbd4
sudo mount -t ext4 -o data=journal /dev/nbd4 /tmp/nbd4
mount

sudo bin/cpp-simple-freerun big ramdisk+buse+ext4-fj /tmp/nbd4

# CLEANUP

sudo umount /tmp/nbd4

# Now close buselfs!

##### (ENCRYPTED) BUSE+NILFS2

sudo /home/odroid/bd3/repos/buselfs/build/buselfs --default-password create nbd5 > ~/bd3/nbd5.debug-log 2>&1 &
sudo tail -f ~/bd3/nbd5.debug-log
# WAIT!
sudo mkfs -t nilfs2 /dev/nbd5
sudo mount -t nilfs2 /dev/nbd5 /tmp/nbd5

sudo bin/cpp-simple-freerun big ramdisk+newbuse+nilfs2 /tmp/nbd5

# CLEANUP

sudo umount /tmp/nbd5

# Now close buselfs!

##### (ENCRYPTED) BUSE+F2FS

sudo /home/odroid/bd3/repos/buselfs/build/buselfs --default-password create nbd6 > ~/bd3/nbd6.debug-log 2>&1 &
sudo tail -f ~/bd3/nbd6.debug-log
# WAIT!
sudo mkfs -t f2fs /dev/nbd6
sudo mount -t f2fs /dev/nbd6 /tmp/nbd6

sudo bin/cpp-simple-freerun big ramdisk+newbuse+f2fs /tmp/nbd6

# CLEANUP

sudo umount /tmp/nbd6

# Now close buselfs!

##### (ENCRYPTED) BUSE+LOGFS

sudo /home/odroid/bd3/repos/buselfs/build/buselfs --default-password create nbd7 > ~/bd3/nbd7.debug-log 2>&1 &
sudo tail -f ~/bd3/nbd7.debug-log
# WAIT!
sudo mkfs -t logfs /dev/nbd7
# COMFIRM!
sudo mount -t logfs /dev/nbd7 /tmp/nbd7

sudo bin/cpp-simple-freerun big ramdisk+newbuse+logfs /tmp/nbd7

# CLEANUP

sudo umount /tmp/nbd7

# Now close buselfs!

##### (ENCRYPTED) BUSE+EXT4OJ

sudo /home/odroid/bd3/repos/buselfs/build/buselfs --default-password create nbd8 > ~/bd3/nbd8.debug-log 2>&1 &
sudo tail -f ~/bd3/nbd8.debug-log
# WAIT!
sudo mkfs -t ext4 /dev/nbd8
sudo mount -t ext4 /dev/nbd8 /tmp/nbd8

sudo bin/cpp-simple-freerun big ramdisk+newbuse+ext4-oj /tmp/nbd8

# CLEANUP

sudo umount /tmp/nbd8

# Now close buselfs!

##### (ENCRYPTED) BUSE+EXT4FJ

sudo /home/odroid/bd3/repos/buselfs/build/buselfs --default-password create nbd9 > ~/bd3/nbd9.debug-log 2>&1 &
sudo tail -f ~/bd3/nbd9.debug-log
# WAIT!
sudo mkfs -t ext4 /dev/nbd9
sudo mount -t ext4 -o data=journal /dev/nbd9 /tmp/nbd9

sudo bin/cpp-simple-freerun big ramdisk+newbuse+ext4-fj /tmp/nbd9

# CLEANUP

sudo umount /tmp/nbd9

# Now close buselfs!

# BUSE+AES-XTS+NILFS2

sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd10 2> ~/bd3/debug-nbd10.debug-log &
sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-urandom luksFormat /dev/nbd10
# YES
# password: t
sudo cryptsetup open --type luks /dev/nbd10 nbd10
# password: t
sudo mkfs -t nilfs2 /dev/mapper/nbd10
sudo mount -t nilfs2 /dev/mapper/nbd10 /tmp/nbd10

sudo bin/cpp-simple-freerun big ramdisk+buse+aes-xts+nilfs2 /tmp/nbd10

# CLEANUP
sudo umount /tmp/nbd10
sudo cryptsetup close nbd10
# Now close BUSE first...

# BUSE+AES-XTS+F2FS

sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd11 2> ~/bd3/debug-nbd11.debug-log &
sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-urandom luksFormat /dev/nbd11
# YES
# password: t
sudo cryptsetup open --type luks /dev/nbd11 nbd11
# password: t
sudo mkfs -t f2fs /dev/mapper/nbd11
sudo mount -t f2fs /dev/mapper/nbd11 /tmp/nbd11

sudo bin/cpp-simple-freerun big ramdisk+buse+aes-xts+f2fs /tmp/nbd11
# CLEANUP
sudo umount /tmp/nbd11
sudo cryptsetup close nbd11
# Now close BUSE first...

# BUSE+AES-XTS+LOGFS

sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd12 2> ~/bd3/debug-nbd12.debug-log &
sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-urandom luksFormat /dev/nbd12
# YES
# password: t
sudo cryptsetup open --type luks /dev/nbd12 nbd12
# password: t
sudo mkfs -t logfs /dev/mapper/nbd12
# CONFIRM
sudo mount -t logfs /dev/mapper/nbd12 /tmp/nbd12

sudo bin/cpp-simple-freerun big ramdisk+buse+aes-xts+logfs /tmp/nbd12
# CLEANUP
sudo umount /tmp/nbd12
sudo cryptsetup close nbd12
# Now close BUSE first...

# BUSE+AES-XTS+EXT4OJ

sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd13 2> ~/bd3/debug-nbd13.debug-log &
sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-urandom luksFormat /dev/nbd13
# YES
# password: t
sudo cryptsetup open --type luks /dev/nbd13 nbd13
# password: t
sudo mkfs -t ext4 /dev/mapper/nbd13
sudo mount -t ext4 /dev/mapper/nbd13 /tmp/nbd13

sudo bin/cpp-simple-freerun big ramdisk+buse+aes-xts+ext4-oj /tmp/nbd13
# CLEANUP
sudo umount /tmp/nbd13
sudo cryptsetup close nbd13
# Now close BUSE first...

# BUSE+AES-XTS+EXT4FJ

sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd14 2> ~/bd3/debug-nbd14.debug-log &
sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-urandom luksFormat /dev/nbd14
# YES
# password: t
sudo cryptsetup open --type luks /dev/nbd14 nbd14
# password: t
sudo mkfs -t ext4 /dev/mapper/nbd14
sudo mount -t ext4 -o data=journal /dev/mapper/nbd14 /tmp/nbd14

sudo bin/cpp-simple-freerun big ramdisk+buse+aes-xts+ext4-fj /tmp/nbd14
# CLEANUP
sudo umount /tmp/nbd14
sudo cryptsetup close nbd14
# Now close BUSE first...
