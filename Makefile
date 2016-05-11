SHELL = /bin/sh
CC = gcc
CFLAGS = -Wall
SOURCES = $(wildcard *.c)

.SUFFIXES:
.SUFFIXES: .c
.PHONY: clean all

all: $(subst .c,,$(SOURCES))

ioctl: $(CC) $(CFLAGS) cpp-freerun.c -o bin/cpp-freerun -lenergymon-default -lpthread

%:
    $(CC) $(CFLAGS) $@.c -o bin/$@

clean:
    rm -f bin/*
