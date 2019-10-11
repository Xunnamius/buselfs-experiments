#!/bin/bash
# Throttle CPU settings
set -e

# Must run script with root privileges
if [ `id -u` -ne 0 ]
then
  echo "must be run with root privileges"
  exit 1
fi

# Throttle the LITTLE cores
for ((i=0; i<=3; i++))
do
  echo 200000 > /sys/devices/system/cpu/cpu$i/cpufreq/scaling_max_freq
done

# Throttle the BIG cores
for ((i=4; i<=7; i++))
do
  echo 200000 > /sys/devices/system/cpu/cpu$i/cpufreq/scaling_max_freq
done

echo "(successfully throttled odroid cpu clocks)"
