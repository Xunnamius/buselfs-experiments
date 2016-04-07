cd /var/netshare/repositories/xunnamius/lfs
fusermount -u /tmp/fuse
rm -f /var/netshare/repositories/xunnamius/lfs/lfslog
rm -rf /tmp/fuse
mkdir /tmp/fuse
./lfs /tmp/fuse
cd -
