#!/bin/bash

writeto=$1
coretype=$2
fstype=$3

`dd if=/dev/zero of=${writeto} bs=512 count=25000 conv=fdatasync oflag=direct >> results/shmoo.${coretype}.${fstype}.results 2>&1`