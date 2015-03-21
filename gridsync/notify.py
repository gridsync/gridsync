#!/usr/bin/python
 
#import pygtk
#pygtk.require('2.0')
import pynotify
import sys
 
if __name__ == '__main__':
    if not pynotify.init("Basics"):
        sys.exit(1)
 
    n = pynotify.Notification("Summary", "This is some sample content")
 
    if not n.show():
        print "Failed to send notification"
        sys.exit(1)
