echo 3 | sudo tee /proc/sys/vm/drop_caches
dd if=/dev/zero of=$1 bs=1M count=100 conv=fdatasync
