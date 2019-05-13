SHELL = /bin/sh
CC = gcc
CFLAGS = -Wall -D_GNU_SOURCE vendor/energymon/energymon-time-util.c -I.

include config/vars.mk

.PHONY: clean all

all: seq rnd

print_config:
	echo $(CONFIG_COMPILE_FLAGS)

seq:
	$(CC) $(CFLAGS) experiments/sequential-freerun.c $(CONFIG_COMPILE_FLAGS) -o bin/sequential-freerun -lenergymon-default -lpthread
	$(CC) $(CFLAGS) experiments/sequential-freerun-wcs.c $(CONFIG_COMPILE_FLAGS) -o bin/sequential-freerun-wcs -lenergymon-default -lpthread

rnd:
	$(CC) $(CFLAGS) experiments/random-freerun.c $(CONFIG_COMPILE_FLAGS) -o bin/random-freerun -lenergymon-default -lpthread
	$(CC) $(CFLAGS) experiments/random-freerun-wcs.c $(CONFIG_COMPILE_FLAGS) -g -O0 -o bin/random-freerun-wcs -lenergymon-default -lpthread

clean:
	rm -rf bin/*
