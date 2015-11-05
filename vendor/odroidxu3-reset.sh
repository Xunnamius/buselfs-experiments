#!/bin/bash
# Reset CPU settings

# Must run script with root privileges
if [ `id -u` -ne 0 ]
then
  echo "Please run with root privileges"
  exit 1
fi

echo 1 > /sys/bus/i2c/drivers/INA231/3-0040/enable
echo 1 > /sys/bus/i2c/drivers/INA231/3-0041/enable
echo 1 > /sys/bus/i2c/drivers/INA231/3-0044/enable
echo 1 > /sys/bus/i2c/drivers/INA231/3-0045/enable

# Reset the LITTLE cores
for ((i=0; i<=3; i++))
do
  echo 1400000 > /sys/devices/system/cpu/cpu$i/cpufreq/scaling_max_freq
done

# Reset the BIG cores
for ((i=4; i<=7; i++))
do
  echo 2000000 > /sys/devices/system/cpu/cpu$i/cpufreq/scaling_max_freq
done
