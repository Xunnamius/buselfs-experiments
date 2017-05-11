SHELL = /bin/sh
CC = gcc
CFLAGS = -Wall -D_GNU_SOURCE vendor/energymon/energymon-time-util.c

.PHONY: clean all

all: seq rnd

seq:
	$(CC) $(CFLAGS) cpp-sequential-freerun.c -o bin/cpp-sequential-freerun -lenergymon-default -lpthread

rnd:
	$(CC) $(CFLAGS) cpp-random-freerun.c -o bin/cpp-random-freerun -lenergymon-default -lpthread

clean:
	rm -rf bin/*
