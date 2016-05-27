#!/bin/bash

writeto=$1
coretype=$2
fstype=$3

echo 1 | sudo tee /proc/sys/vm/drop_caches
#`dd if=${writeto} of=/dev/null bs=1024 count=20000 iflag=direct >> results/shmoo.${coretype}.${fstype}.results 2>&1`
`dd if=${writeto} of=/dev/null bs=512 count=25000 iflag=direct`
