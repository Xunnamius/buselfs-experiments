SHELL = /bin/sh
CC = gcc
CFLAGS = -Wall -D_GNU_SOURCE vendor/energymon/energymon-time-util.c

.PHONY: clean all

seq:
	$(CC) $(CFLAGS) cpp-sequential-freerun.c -o bin/cpp-simple-freerun -lenergymon-default -lpthread

rnd:
	$(CC) $(CFLAGS) cpp-random-freerun.c -o bin/cpp-simple-freerun -lenergymon-default -lpthread

clean:
	rm -f bin/*
