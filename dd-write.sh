#!/bin/bash

writeto=$1
coretype=$2
fstype=$3

`dd if=/dev/urandom of=${writeto} bs=512 count=5000 conv=fdatasync oflag=direct >> results/shmoo.${coretype}.${fstype}.results 2>&1`
