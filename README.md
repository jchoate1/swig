SoftWare Image Generator - swig.py

This was a hackathon project from March 2018.

This is a tool that uses the curses library to look at an Arista Software Image
and add new RPMs to it.  When run with no arguments, it will expand the SWI file
and determine which RPMs need to be updated, and only display those in the menu.

This is a very time consuming process, so it is better to run it with the '-a'
option which tells it to just include all RPMs, and puts the oweness on the user
to determine which RPMs should be included in the SWI.

So for most all purposes, run it with "swig.py -a".
