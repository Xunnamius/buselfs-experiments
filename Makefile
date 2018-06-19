SHELL = /bin/sh
CC = gcc
CFLAGS = -Wall -D_GNU_SOURCE vendor/energymon/energymon-time-util.c

include config/vars.mk

.PHONY: clean all

all: seq rnd

print_config:
	echo $(CONFIG_COMPILE_FLAGS)

seq:
	$(CC) $(CFLAGS) experiments/cpp-sequential-freerun.c $(CONFIG_COMPILE_FLAGS) -o bin/cpp-sequential-freerun -lenergymon-default -lpthread

rnd:
	$(CC) $(CFLAGS) experiments/cpp-random-freerun.c $(CONFIG_COMPILE_FLAGS) -o bin/cpp-random-freerun -lenergymon-default -lpthread

clean:
	rm -rf bin/*
