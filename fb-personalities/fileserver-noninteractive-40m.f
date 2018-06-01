#
# CDDL HEADER START
#
# The contents of this file are subject to the terms of the
# Common Development and Distribution License (the "License").
# You may not use this file except in compliance with the License.
#
# You can obtain a copy of the license at usr/src/OPENSOLARIS.LICENSE
# or http://www.opensolaris.org/os/licensing.
# See the License for the specific language governing permissions
# and limitations under the License.
#
# When distributing Covered Code, include this CDDL HEADER in each
# file and include the License file at usr/src/OPENSOLARIS.LICENSE.
# If applicable, add the following below this CDDL HEADER, with the
# fields enclosed by brackets "[]" replaced with your own identifying
# information: Portions Copyright [yyyy] [name of copyright owner]
#
# CDDL HEADER END
#
#
# Copyright 2008 Sun Microsystems, Inc.  All rights reserved.
# Use is subject to license terms.
#

set $dir=/tmp/nbd6
set $nfiles=2
set $meandirwidth=2
set $meanfilesize=40m
set $nthreads=1
set $iosize=40m
set $meanappendsize=16k

define fileset name=bigfileset,path=$dir,size=$meanfilesize,entries=$nfiles,dirwidth=$meandirwidth,prealloc=80,reuse

define process name=filereader,instances=1
{
  thread name=filereaderthread,memsize=10m,instances=$nthreads
  {
    flowop createfile name=createfile1,filesetname=bigfileset,fd=1,dsync
    flowop writewholefile name=wrtfile1,srcfd=1,fd=1,iosize=$iosize,dsync
    flowop closefile name=closefile1,fd=1
    flowop openfile name=openfile1,filesetname=bigfileset,fd=1,dsync
    flowop appendfilerand name=appendfilerand1,iosize=$meanappendsize,fd=1,dsync
    flowop closefile name=closefile2,fd=1
    flowop openfile name=openfile2,filesetname=bigfileset,fd=1
    flowop readwholefile name=readfile1,fd=1,iosize=$iosize,directio
    flowop closefile name=closefile3,fd=1
    flowop deletefile name=deletefile1,filesetname=bigfileset
    flowop statfile name=statfile1,filesetname=bigfileset
  }
}

echo  "File-server Version 3.0-custom-noninteractive personality successfully loaded"
# usage "Usage: set \$dir=<dir>"
# usage "       set \$meanfilesize=<size>     defaults to $meanfilesize"
# usage "       set \$nfiles=<value>      defaults to $nfiles"
# usage "       set \$nthreads=<value>    defaults to $nthreads"
# usage "       set \$meanappendsize=<value>  defaults to $meanappendsize"
# usage "       set \$iosize=<size>  defaults to $iosize"
# usage "       set \$meandirwidth=<size> defaults to $meandirwidth"
# usage "       run runtime (e.g. run 60)"
run 60
