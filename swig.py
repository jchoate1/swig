#!/usr/bin/python

import sys
import argparse
import os
import errno
import glob
import re
import optparse
# NOTE: This script requires the presence of curses-menu which must
# be previously installed (sudo pip install curses-menu)
import curses
import curses.wrapper

import tempfile
import Swi

import pdb

eosSwi = "/images/EOS.swi"
eosIntSwi = "/images/EOS-INT.swi"
swiHistory = "/RPMS/.lastSwiUpdate"
dryRun = False
verbose = False
showAll = False
clearHistory = False
international = False

class Picker:
    """Allows you to select from a list with curses"""
    stdscr = None
    win = None
    title = ""
    arrow = ""
    footer = ""
    more = ""
    c_selected = ""
    c_empty = ""
    
    cursor = 0
    offset = 0
    selected = 0
    selcount = 0
    aborted = False
    ### TODO - need to check for errored sizes here for term width and len
    rows,columns = os.popen( 'stty size', 'r' ).read().split()
    window_height = int(rows)-10
    window_width = int(columns)-10
    all_options = []
    length = 0
    
    def curses_start(self):
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.win = curses.newwin(
            5 + self.window_height,
            self.window_width,
            2,
            4
        )
    
    def curses_stop(self):
        curses.nocbreak()
        self.stdscr.keypad(0)
        curses.echo()
        curses.endwin()

    def getSelected(self):
        if self.aborted == True:
            return( False )

        ret_s = filter(lambda x: x["selected"], self.all_options)
        ret = map(lambda x: x["label"], ret_s)
        return( ret )
        
    def redraw(self):
        self.win.clear()
        self.win.border(
            self.border[0], self.border[1],
            self.border[2], self.border[3],
            self.border[4], self.border[5],
            self.border[6], self.border[7]
        )
        self.win.addstr(
            self.window_height + 4, 5, " " + self.footer + " "
        )
        
        position = 0
        range = self.all_options[self.offset:self.offset+self.window_height+1]
        for option in range:
            if option["selected"] == True:
                line_label = self.c_selected + " "
            else:
                line_label = self.c_empty + " "
            
            self.win.addstr(position + 2, 5, line_label + option["label"])
            position = position + 1
            
        # hint for more content above
        if self.offset > 0:
            self.win.addstr(1, 5, self.more)
        
        # hint for more content below
        if self.offset + self.window_height <= self.length - 2:
            self.win.addstr(self.window_height + 3, 5, self.more)
        
        self.win.addstr(0, 5, " " + self.title + " ")
        self.win.addstr(
            0, self.window_width - 8,
            " " + str(self.selcount) + "/" + str(self.length) + " "
        )
        self.win.addstr(self.cursor + 2,1, self.arrow)
        self.win.refresh()

    def check_cursor_up(self):
        if self.cursor < 0:
            self.cursor = 0
            if self.offset > 0:
                self.offset = self.offset - 1
    
    def check_cursor_down(self):
        if self.cursor >= self.length:
            self.cursor = self.cursor - 1
    
        if self.cursor > self.window_height:
            self.cursor = self.window_height
            self.offset = self.offset + 1
            
            if self.offset + self.cursor >= self.length:
                self.offset = self.offset - 1
    
    def curses_loop(self, stdscr):
        while 1:
            self.redraw()
            c = stdscr.getch()
            
            if c == ord('q') or c == ord('Q'):
                self.aborted = True
                break
            elif c == curses.KEY_UP:
                self.cursor = self.cursor - 1
            elif c == curses.KEY_DOWN:
                self.cursor = self.cursor + 1
            #elif c == curses.KEY_PPAGE:
            #elif c == curses.KEY_NPAGE:
#            elif c == ord('c') or c == ord('C'):
#               for option in self.all_options:
#                  self.all_options.append({
#                     "selected" : False
#                  })
            elif c == ord(' '):
                self.all_options[self.selected]["selected"] = \
                    not self.all_options[self.selected]["selected"]
            elif c == 10:
                break
                    
            # deal with interaction limits
            self.check_cursor_up()
            self.check_cursor_down()

            # compute selected position only after dealing with limits
            self.selected = self.cursor + self.offset
            
            temp = self.getSelected()
            self.selcount = len(temp)
    
    def __init__(
        self, 
        options, 
        title='Select', 
        arrow="-->",
        footer="Space = toggle, Enter = accept, q = cancel",
        more="...",
        border="||--++++",
        c_selected="[X]",
        c_empty="[ ]",
        prevSetFile=""
    ):
        self.title = title
        self.arrow = arrow
        self.footer = footer
        self.more = more
        self.border = border
        self.c_selected = c_selected
        self.c_empty = c_empty
        
        self.all_options = []
        
        previousSelections = ""
        if len( prevSetFile ):
           filePtr = open( prevSetFile, "r" )
           previousSelections = filePtr.read()
           filePtr.close()
        for option in options:
           wasThere = False
           if option.split("\t")[0] in previousSelections:
              wasThere = True
           self.all_options.append({
              "label": option,
              "selected" : wasThere
           })
           self.length = len(self.all_options)
        
        self.curses_start()
        curses.wrapper( self.curses_loop )
        self.curses_stop()


def presentInSwi( imageList, package ):
   ## This function needs to query the swi for
   ## the presnce of the package within the swi file
   ## return True if it is there, False if not
   #return False
   expression = '([A-z0-9]*\-*([A-z0-9\-]*)\-[0-9]+\.[0-9]+\.[0-9]+)\-([0-9]+).*'
   p = re.compile( expression )
   proposed = p.match( package )
   if not proposed:
      return False
   basePackage = proposed.group(1)
   newVersion = proposed.group(3)
   installedPkg = next((s for s in imageList if basePackage in s), None)
   if not installedPkg:
      return False
   current = p.match( installedPkg )
   curInstPackage = current.group(1)
   curInstVersion = current.group(3)

   if ( newVersion > curInstVersion ):
      #print ("%s is not up to date and available for update" % package)
      return False
   #print ("%s is already current or newer and is not available for update" % package)
   return True

   
def getInstalledPkgVersions( image ):
   tmpdir = tempfile.mkdtemp()
   print "Extracting %s to %s to get currently installed packages" % ( image, tmpdir )
   Swi.extract.extract( image, Swi.SwiOptions( dirname=tmpdir,
                                               use_existing=True ) )
   rootDir = os.path.join( tmpdir, 'rootfs-i386.dir' )

   ## TODO - Look into this baseRpmModule stuff.  It is used in /src/EosUtils/Swi/flavor.py
   ## imported rpm as baseRpmModule, but I cannot find the addMacro or ts definitions.
   ## This might do what I want to do in a less kludgey way.  Do this as a refinement.
   ## looks to be defined in Artools...
   # Find out which RPMs are actually present in the swi ...
   # rpmDbPath = os.path.normpath( os.path.join( rootDir, 'var/lib/rpm' ) )
   # # pylint: disable=E1101
   # baseRpmModule.addMacro( "_dbpath", rpmDbPath )
   # ts = baseRpmModule.ts()
   # swiRpms = set( [ rpm[ 'name' ] for rpm in ts.dbMatch() ] )
   # # ... and only consider those for removal
   # setDiff = set( sharedExcludes ) - swiRpms

   # Generate a list of the packages installed in the current swi
   installedPkgs = list()
   installedPkgs = os.popen( "sudo chroot %s rpm -qa" % rootDir ).read().split()
   
   print "Cleaning up and removing the extracted swi directory", tmpdir
   Swi.run( [ 'sudo', 'rm', '-rf', tmpdir ] )
   return installedPkgs
   
def updateSwi( ):
   global international
   rows,cols = os.popen( 'stty size', 'r' ).read().split()
   rawRpmList = glob.glob( "/RPMS/*.rpm" )
   rawRpmList.sort()
   rpmDict = {}
   
   if international:
      swiImage = eosIntSwi
   else:
      swiImage = eosSwi
   swiUpdateCommand = "sudo swi rpm " + swiImage + " -Uvh"

   currentList = list()
   if not showAll:
      currentList = getInstalledPkgVersions( swiImage )
   rpmList = list()
   for rpm in rawRpmList:
      versionStr = os.popen("rpm -qp %s" % rpm).read()
      check = presentInSwi(currentList, versionStr)
      if (( check == False ) or showAll ):
         longStr = ( "%s\t\t%s" % ( rpm, versionStr ) )
         width = int(cols) - 40
         outStr = (longStr[:width] + '...') if (len(longStr) > width) else longStr
         rpmList.append( outStr )
         ## Save the full name for the swi command - don't use truncated
         rpmDict[outStr] = rpm
   includedRpmList = opts = Picker(
      title = 'Select rpms to add to SWI',
      options = rpmList,
      prevSetFile = swiHistory if os.path.isfile( swiHistory ) else ""
      ).getSelected()
   if (len(includedRpmList)):
      for rpm in includedRpmList:
         swiUpdateCommand += " " + rpmDict[ rpm ].split("\t")[0]
      print swiUpdateCommand
      filePtr = open( swiHistory, "w" )
      filePtr.write( swiUpdateCommand + "\n" )
      filePtr.close()
      if not dryRun:
         os.system( swiUpdateCommand )


def updateHandler( args=sys.argv[1:] ):
   global dryRun
   global showAll
   global international
   op = optparse.OptionParser(
         prog=sys.argv[0],
         usage="usage: %prog [options]" )
   op.add_option( '-d', '--dryRun', action='store_true',
                  help='Skip the system command to build the swi at the end.')
   op.add_option( '-a', '--all', action='store_true',
                  help='Show all packages regardless of upgradeability.' )
   op.add_option( '-c', '--clear', action='store_true',
                  help='Clear prior selection history' )
   op.add_option( '-i', '--international', action='store_true',
                  help='Build the international SWI instead.' )
   opts, args = op.parse_args( args )

   if opts.clear:
      os.remove( swiHistory )
   if opts.all:
      showAll = True;
   if opts.dryRun:
      dryRun = True
   if opts.international:
      international = True
      
   updateSwi( )
   
   
if __name__ == "__main__":
   updateHandler()

