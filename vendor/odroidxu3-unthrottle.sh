#!/bin/bash
# Unthrottle (reset) CPU settings
set -e

# Must run script with root privileges
if [ `id -u` -ne 0 ]
then
  echo "must be run with root privileges"
  exit 1
fi

# Unthrottle the LITTLE cores
for ((i=0; i<=3; i++))
do
  echo 1400000 > /sys/devices/system/cpu/cpu$i/cpufreq/scaling_max_freq
done

# Unthrottle the BIG cores
for ((i=4; i<=7; i++))
do
  echo 2000000 > /sys/devices/system/cpu/cpu$i/cpufreq/scaling_max_freq
done

echo "(successfully unthrottled odroid cpu clocks)"
