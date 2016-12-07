echo 3 | sudo tee /proc/sys/vm/drop_caches
dd if=$1 of=/dev/null bs=1M count=75
