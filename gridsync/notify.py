#!/usr/bin/python
 
#import pygtk
#pygtk.require('2.0')
#import pynotify
import sys
import notify2

notify2.init('app name')

n = notify2.Notification("Summary",
                         "Some body text",
                         "notification-message-im"   # Icon name
                        )
n.show()

