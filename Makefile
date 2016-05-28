SHELL = /bin/sh
CC = gcc
CFLAGS = -Wall

.PHONY: clean test run

freerun:
	$(CC) $(CFLAGS) cpp-freerun.c -o bin/cpp-freerun -lenergymon-default -lpthread

clean:
	rm -f bin/*

test:
	sudo ./bin/cpp-freerun big testfs /home/odroid/bd3/repos/energy-AES-1/test

run:
	echo 'If you did not call `make freerun` or did not run setupfilesystems.sh, then ctrl+c NOW!'
	sleep 5
	sudo ./bin/cpp-freerun 01-kext4-normal /home/odroid/bd3/fuse/mnt/01-kext4-normal/write
	sudo ./bin/cpp-freerun 02-kext4-fuse-ext4 /home/odroid/bd3/fuse/mnt/02-kext4-fuse-ext4/write
	sudo ./bin/cpp-freerun 03-kext4-fuse-ext4-dmc /home/odroid/bd3/fuse/mnt/03-kext4-fuse-ext4-dmc/write/write
	sudo ./bin/cpp-freerun 04-kext4-dmc-fuse-ext4 /home/odroid/bd3/fuse/mnt/04-kext4-dmc-fuse-ext4/write/write
	#sudo ./bin/cpp-freerun 05-kext4-fuse-lfs /home/odroid/bd3/fuse/mnt/05-kext4-fuse-lfs/write
	#sudo ./bin/cpp-freerun 06-kext4-fuse-lfs-chacha-poly /home/odroid/bd3/fuse/mnt/06-kext4-fuse-lfs-chacha-poly/write
	sudo ./bin/cpp-freerun 07-rdext4-normal /home/odroid/bd3/fuse/mnt/07-rdext4-normal/write
	sudo ./bin/cpp-freerun 08-rdext4-fuse-ext4 /home/odroid/bd3/fuse/mnt/08-rdext4-fuse-ext4/write
	sudo ./bin/cpp-freerun 09-rdext4-fuse-ext4-dmc /home/odroid/bd3/fuse/mnt/09-rdext4-fuse-ext4-dmc/write/write
	sudo ./bin/cpp-freerun 10-rdext4-dmc-fuse-ext4 /home/odroid/bd3/fuse/mnt/10-rdext4-dmc-fuse-ext4/write/write
	#sudo ./bin/cpp-freerun 11-rdext4-fuse-lfs /home/odroid/bd3/fuse/mnt/11-rdext4-fuse-lfs/write
	#sudo ./bin/cpp-freerun 12-rdext4-fuse-lfs-chacha-poly /home/odroid/bd3/fuse/mnt/12-rdext4-fuse-lfs-chacha-poly/write
