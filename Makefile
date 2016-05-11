SHELL = /bin/sh
CC = gcc
CFLAGS = -Wall

.PHONY: clean

freerun:
	$(CC) $(CFLAGS) cpp-freerun.c -o bin/cpp-freerun -lenergymon-default -lpthread

clean:
	rm -f bin/*
