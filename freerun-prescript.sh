fusermount -u /tmp/fuse
rm -f /var/netshare/repositories/xunnamius/lfs/lfslog
rm -rf /tmp/fuse
mkdir /tmp/fuse
sh -c "/var/netshare/repositories/xunnamius/lfs/lfs /tmp/fuse"
