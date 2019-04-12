#!/usr/bin/env python
# Copyright (c) 2017 Arista Networks, Inc.  All rights reserved.
# Arista Networks, Inc. Confidential and Proprietary.
"""============================================================================
updateSwi.py             -- patch up an existing EOS image with whatever is in
Feb  9, 2017/wsawyer        the RPMs directory, leaving out the packages that
                            we know we don't need, and querying about the rest.
============================================================================"""
import sys
import argparse
import os
import errno
import glob

eosSwi = "/images/EOS.swi"
eosIntSwi = "/images/EOS-INT.swi"
savedEosIntSwiTemplate = "/images/saved-%d-EOS-INT.swi"
swiUpdateCommand = "sudo swi rpm " + eosSwi + " -Uvh " #  followed by RPMs

excluded = ( "-sim.i686.rpm",
             "-gcov.i686.rpm",
             "-devel.i686.rpm",
             "-testlib.i686.rpm",
             "-stest.i686.rpm",
             "-ptest.i686.rpm",
             "-all.i686.rpm",
             "-golib.i686.rpm",
             "-debuginfo.i686.rpm",
             )

def getYesNo( prompt, default=None ):
   question = " (yes/no)?"
   if default:
      default = default.lower()
      if default.startswith( "y" ):
         question = " (YES/no)?"
      elif default.startswith( "n" ):
         question = " (yes/NO)?"
   while True:
      print prompt + question,
      answer = sys.stdin.readline().rstrip( "\n\r" ).lower()
      if len( answer ) == 0 and default != None:
         answer = default
      if answer == 'y' or answer == 'yes':
         return True
      elif answer == 'n' or answer == 'no':
         return False
      else:
         print( "please answer yes or no" )

def getRawRpmList():
   return glob.glob( "/RPMS/*.rpm" )

def makeSwisTheSame():
   try:
      eosStat = os.stat( eosSwi )
      eosIntStat = os.stat( eosIntSwi )
   except OSError as ose:
      if ose.errno == errno.ENOENT:
         print( "Didn't find %s or %s: in chroot?" % ( eosSwi, eosIntSwi ) )
      else:
         raise
      return
   if eosStat.st_ino == eosIntStat.st_ino: # if one is a symlink to the other
      return
   makeSymLink = getYesNo(
      "EOS.swi and EOS-INT.swi are not the same. Make one a sym-link?",
      default="yes" )
   if makeSymLink:
      savedEosIntSwi = savedEosIntSwiTemplate % os.getpid()
      cmd = "sudo mv %s %s" % ( eosIntSwi, savedEosIntSwi )
      print cmd
      os.system( cmd )
      cmd = "sudo ln -s %s %s" % ( eosSwi, eosIntSwi )
      print cmd
      os.system( cmd )

def updateSwi():
   global swiUpdateCommand
   makeSwisTheSame()
   rawRpmList = getRawRpmList()
   rpmList = list()
   for rpm in rawRpmList:
      isExcluded = False
      for exc in excluded:
         if exc in rpm:
            print( "Excluding %s" % rpm )
            isExcluded = True
            break
      if not isExcluded:
         rpmList.append( rpm )
   includedRpmList = list()
   for rpm in rpmList:
      include = getYesNo( "include   %s?" % rpm, default="yes" )
      if include:
         includedRpmList.append( rpm )
   if len( includedRpmList ) == 0:
      print( "No RPMs selected for SWI update. Quitting" )
      return
   for rpm in includedRpmList:
      swiUpdateCommand += " " + rpm
   print swiUpdateCommand
   doIt = getYesNo( "OK?" )
   if doIt:
      os.system( swiUpdateCommand )

if __name__ == "__main__":
   argparser = argparse.ArgumentParser( description=__doc__,
      formatter_class=argparse.RawDescriptionHelpFormatter )
   argparser.add_argument( "--verbose", dest="verbose",
                           action="store_true", default=False )
   args = argparser.parse_args()
   updateSwi()
