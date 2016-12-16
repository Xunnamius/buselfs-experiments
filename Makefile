SHELL = /bin/sh
CC = gcc
CFLAGS = -Wall -D_GNU_SOURCE vendor/energymon/energymon-time-util.c

.PHONY: clean test run

freerun:
	$(CC) $(CFLAGS) cpp-freerun.c -o bin/cpp-freerun -lenergymon-default -lpthread

simple:
	$(CC) $(CFLAGS) cpp-simple-freerun.c -o bin/cpp-simple-freerun -lenergymon-default -lpthread

simpler:
	$(CC) $(CFLAGS) cpp-simple-freerun.c -o bin/cpp-simple-freerun

duration:
	$(CC) $(CFLAGS) cpp-duration.c -o bin/cpp-duration

clean:
	rm -f bin/*

test:
	sudo ./bin/cpp-freerun big testfs /home/odroid/bd3/repos/energy-AES-1/test

run:
	@echo 'If you did not call `make freerun` or did not run setupfilesystems.sh, then ctrl+c NOW!'
	sleep 5
	#sudo ./bin/cpp-freerun big 01-kext4-normal /home/odroid/bd3/fuse/mnt/01-kext4-normal/write
	#sudo ./bin/cpp-freerun big 02-kext4-fuse-ext4 /home/odroid/bd3/fuse/mnt/02-kext4-fuse-ext4/write
	#sudo ./bin/cpp-freerun big 03-kext4-fuse-ext4-dmc /home/odroid/bd3/fuse/mnt/03-kext4-fuse-ext4-dmc/write/write
	#sudo ./bin/cpp-freerun big 04-kext4-dmc-fuse-ext4 /home/odroid/bd3/fuse/mnt/04-kext4-dmc-fuse-ext4/write/write
	#sudo ./bin/cpp-freerun big 05-kext4-fuse-lfs /home/odroid/bd3/fuse/mnt/05-kext4-fuse-lfs/write
	#sudo ./bin/cpp-freerun big 06-kext4-fuse-lfs-chacha-poly /home/odroid/bd3/fuse/mnt/06-kext4-fuse-lfs-chacha-poly/write
	#sudo ./bin/cpp-freerun big 07-rdext4-normal /media/rd/07-rdext4-normal/write
	sudo ./bin/cpp-freerun big 08-rdext4-fuse-ext4 /media/rd/08-rdext4-fuse-ext4/write
	sudo ./bin/cpp-freerun big 09-rdext4-fuse-ext4-dmc /media/rd/09-rdext4-fuse-ext4-dmc/write/write
	#sudo ./bin/cpp-freerun big 10-rdext4-dmc-fuse-ext4 /media/rd/10-rdext4-dmc-fuse-ext4/write/write
	sudo ./bin/cpp-freerun big 11-rdext4-fuse-lfs /media/rd/11-rdext4-fuse-lfs/write
	#sudo ./bin/cpp-freerun big 12-rdext4-fuse-lfs-chacha-poly /media/rd/12-rdext4-fuse-lfs-chacha-poly/write
