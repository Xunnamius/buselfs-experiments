sudo fusermount -u /media/rd/11-rdext4-fuse-lfs/write
sudo rm -f /media/rd/11-rdext4-fuse-lfs/lfslog
sudo rm -rf /media/rd/11-rdext4-fuse-lfs/write
sudo mkdir -p /media/rd/11-rdext4-fuse-lfs/write
cd /media/rd/11-rdext4-fuse-lfs
sudo sh -c "/home/odroid/bd3/repos/energy-AES-1/vendor/github/lfs/lfs /media/rd/11-rdext4-fuse-lfs/write"
cd -
