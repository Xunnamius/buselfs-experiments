###################
# INIT (run once) #
###################

sudo modprobe nbd
sudo modprobe logfs
sudo modprobe nilfs2
sudo modprobe f2fs

mkdir /tmp/ram0 /tmp/nbd0 /tmp/nbd1 /tmp/nbd2 /tmp/nbd3 /tmp/nbd4 /tmp/nbd5 /tmp/nbd6 /tmp/nbd7 /tmp/nbd8 /tmp/nbd9 /tmp/nbd10 /tmp/nbd11 /tmp/nbd12 /tmp/nbd13 /tmp/nbd14 /tmp/nbd15
mkdir /tmp/config /tmp/run

cp /home/odroid/bd3/repos/buselfs/config/zlog_conf.conf /tmp/config/

sudo mount -t tmpfs -o size=1024M tmpfs /tmp/ram0
mount
