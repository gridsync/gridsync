#!/usr/bin/python
 
#import pygtk
#pygtk.require('2.0')
import pynotify
import sys

def notify(text):
    if not pynotify.init("Basics"):
        sys.exit(1)
 
    n = pynotify.Notification("Gridsync", text)
 
    if not n.show():
        print "Failed to send notification"
        sys.exit(1)
