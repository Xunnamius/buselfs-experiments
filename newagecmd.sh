sudo true
# INIT (run once)
sudo modprobe nbd
sudo modprobe logfs
sudo modprobe nilfs2
sudo modprobe f2fs
sudo mkdir /tmp/ram0 mkdir /tmp/nbd0 /tmp/nbd1 /tmp/nbd2 /tmp/nbd3 /tmp/nbd4 /tmp/nbd5 /tmp/nbd6 /tmp/nbd7 /tmp/nbd8 /tmp/nbd9 /tmp/nbd10 /tmp/nbd11 /tmp/nbd12 /tmp/nbd13 /tmp/nbd14 /tmp/nbd15
cd /home/odroid/bd3/repos/energy-AES-1
cd /tmp/ram0
cd -
sudo modprobe brd rd_nr=1 rd_size=1048576
sudo mkfs.ext4 /dev/ram0
sudo mount -t ext4 /dev/ram0 /tmp/ram0

# CLEANUP
sudo true
sudo umount /tmp/nbd0 /tmp/nbd1 /tmp/nbd2 /tmp/nbd3 /tmp/nbd4 /tmp/nbd5 /tmp/nbd6 /tmp/nbd7 /tmp/nbd8 /tmp/nbd9 /tmp/nbd10 /tmp/nbd11 /tmp/nbd12 /tmp/nbd13 /tmp/nbd14 /tmp/nbd15
sudo cryptsetup close nbd10; sudo cryptsetup close nbd11 sudo cryptsetup close nbd12; sudo cryptsetup close nbd13; sudo cryptsetup close nbd14; sudo cryptsetup close nbd15;
# -- don't copypaste all of this! stop buse first, then do this next line
sudo rm /tmp/ram0/logfs-nbd*.bkstr
sudo sync

# BUSE+LOGFS
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd0 2> ~/bd3/debug-nbd0.log &
sudo mkfs -t logfs /dev/nbd0
sudo mount -t logfs /dev/nbd0 /tmp/nbd0
cd -
sudo bin/cpp-simple-freerun big mmc+buse+logfs /tmp/nbd0

# BUSE+NILFS2
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd1 2> ~/bd3/debug-nbd1.log &
sudo mkfs -t nilfs2 /dev/nbd1
sudo mount -t nilfs2 /dev/nbd1 /tmp/nbd1
cd -
sudo bin/cpp-simple-freerun big mmc+buse+nilfs2 /tmp/nbd1

# BUSE+F2FS
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd2 2> ~/bd3/debug-nbd2.log &
sudo mkfs -t f2fs /dev/nbd2
sudo mount -t f2fs /dev/nbd2 /tmp/nbd2
cd -
sudo bin/cpp-simple-freerun big mmc+buse+f2fs /tmp/nbd2

# BUSE+EXT4OJ
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd3 2> ~/bd3/debug-nbd3.log &
sudo mkfs -t ext4 /dev/nbd3
sudo mount -t ext4 -o data=ordered /dev/nbd3 /tmp/nbd3
cd -
sudo bin/cpp-simple-freerun big mmc+buse+ext4-oj /tmp/nbd3

# BUSE+EXT4FJ
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd4 2> ~/bd3/debug-nbd4.log &
sudo mkfs -t ext4 /dev/nbd4
sudo mount -t ext4 -o data=journal /dev/nbd4 /tmp/nbd4
cd -
sudo bin/cpp-simple-freerun big mmc+buse+ext4-fj /tmp/nbd4

# (ENCRYPTED) EBUSE+LOGFS
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --with-encrypt --size $((1024*1024*900)) /dev/nbd5 2> ~/bd3/debug-nbd5.log &
sudo mkfs -t logfs /dev/nbd5
sudo mount -t logfs /dev/nbd5 /tmp/nbd5
cd -
sudo bin/cpp-simple-freerun big mmc+ebuse+logfs /tmp/nbd5

# (ENCRYPTED) EBUSE+NILFS2
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --with-encrypt --size $((1024*1024*900)) /dev/nbd6 2> ~/bd3/debug-nbd6.log &
sudo mkfs -t nilfs2 /dev/nbd6
sudo mount -t nilfs2 /dev/nbd6 /tmp/nbd6
cd -
sudo bin/cpp-simple-freerun big mmc+ebuse+nilfs2 /tmp/nbd6

# (ENCRYPTED) EBUSE+F2FS
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --with-encrypt --size $((1024*1024*900)) /dev/nbd7 2> ~/bd3/debug-nbd7.log &
sudo mkfs -t f2fs /dev/nbd7
sudo mount -t f2fs /dev/nbd7 /tmp/nbd7
cd -
sudo bin/cpp-simple-freerun big mmc+ebuse+f2fs /tmp/nbd7

# (ENCRYPTED) EBUSE+EXT4OJ
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --with-encrypt --size $((1024*1024*900)) /dev/nbd8 2> ~/bd3/debug-nbd8.log &
sudo mkfs -t ext4 /dev/nbd8
sudo mount -t ext4 -o data=ordered /dev/nbd8 /tmp/nbd8
cd -
sudo bin/cpp-simple-freerun big mmc+ebuse+ext4-oj /tmp/nbd8

# (ENCRYPTED) EBUSE+EXT4FJ
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --with-encrypt --size $((1024*1024*900)) /dev/nbd9 2> ~/bd3/debug-nbd9.log &
sudo mkfs -t ext4 /dev/nbd9
sudo mount -t ext4 -o data=journal /dev/nbd9 /tmp/nbd9
cd -
sudo bin/cpp-simple-freerun big mmc+ebuse+ext4-fj /tmp/nbd9

# BUSE+AES-XTS+LOGFS
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd10 2> ~/bd3/debug-nbd10.log &
sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-urandom luksFormat /dev/nbd10
# YES
# password: badpasswordsarebad
sudo cryptsetup open --type luks /dev/nbd10 nbd10
# password: badpasswordsarebad
sudo mkfs -t logfs /dev/mapper/nbd10
# YES
sudo mount -t logfs /dev/mapper/nbd10 /tmp/nbd10
cd -
sudo bin/cpp-simple-freerun big mmc+buse+aes-xts+logfs /tmp/nbd10

# BUSE+AES-XTS+NILFS2
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd11 2> ~/bd3/debug-nbd11.log &
sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-urandom luksFormat /dev/nbd11
# YES
# password: badpasswordsarebad
sudo cryptsetup open --type luks /dev/nbd11 nbd11
# password: badpasswordsarebad
sudo mkfs -t nilfs2 /dev/mapper/nbd11
sudo mount -t nilfs2 /dev/mapper/nbd11 /tmp/nbd11
cd -
sudo bin/cpp-simple-freerun big mmc+buse+aes-xts+nilfs2 /tmp/nbd11

# BUSE+AES-XTS+F2FS
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd12 2> ~/bd3/debug-nbd12.log &
sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-urandom luksFormat /dev/nbd12
# YES
# password: badpasswordsarebad
sudo cryptsetup open --type luks /dev/nbd12 nbd12
# password: badpasswordsarebad
sudo mkfs -t f2fs /dev/mapper/nbd12
sudo mount -t f2fs /dev/mapper/nbd12 /tmp/nbd12
cd -
sudo bin/cpp-simple-freerun big mmc+buse+aes-xts+f2fs /tmp/nbd12

# BUSE+AES-XTS+EXT4OJ
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd13 2> ~/bd3/debug-nbd13.log &
sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-urandom luksFormat /dev/nbd13
# YES
# password: badpasswordsarebad
sudo cryptsetup open --type luks /dev/nbd13 nbd13
# password: badpasswordsarebad
sudo mkfs -t ext4 /dev/mapper/nbd13
sudo mount -t ext4 /dev/mapper/nbd13 /tmp/nbd13
cd -
sudo bin/cpp-simple-freerun big mmc+buse+aes-xts+ext4-oj /tmp/nbd13

# BUSE+AES-XTS+EXT4FJ
sudo true
cd -
sudo /home/odroid/bd3/repos/BUSE/buselogfs --size $((1024*1024*900)) /dev/nbd14 2> ~/bd3/debug-nbd14.log &
sudo cryptsetup --verbose --cipher aes-xts-plain64 --key-size 512 --hash sha512 --iter-time 5000 --use-urandom luksFormat /dev/nbd14
# YES
# password: badpasswordsarebad
sudo cryptsetup open --type luks /dev/nbd14 nbd14
# password: badpasswordsarebad
sudo mkfs -t ext4 /dev/mapper/nbd14
sudo mount -t ext4 -o data=journal /dev/mapper/nbd14 /tmp/nbd14
cd -
sudo bin/cpp-simple-freerun big mmc+buse+aes-xts+ext4-fj /tmp/nbd14
