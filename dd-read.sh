#!/bin/bash

writeto=$1
coretype=$2
fstype=$3
`( dd if=${writeto} of=/dev/null bs=512 count=5000 conv=fdatasync iflag=direct ) > results/shmoo.${coretype}.${fstype}.results 2>&1`
