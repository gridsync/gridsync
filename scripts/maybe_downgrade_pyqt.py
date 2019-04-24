import platform
import subprocess
import sys


version = platform.mac_ver()[0]

if not version:
    sys.exit("Not a Mac or no version detected; exiting")

major = int(version.split('.')[0])
minor = int(version.split('.')[1])

if (major, minor) < (10, 12):
    print("Older Mac detected ({}); Downgrading SIP, PyQt5...".format(version))
    if (major, minor) >= (10, 10):
        # PyQt5 5.12 fails on macOS 10.11 with "Symbol not found: 
        # __os_activity_create"
        subprocess.call([
            'python', '-m', 'pip', 'install', 'PyQt5==5.11.3',
            'PyQt5-sip==4.19.13'])
    else:
        # PyQt5 5.9(+?) fails on macOS 10.09 with "Symbol not found: 
        # _LSCopyDefaultApplicationURLForURL"
        subprocess.call([
            'python', '-m', 'pip', 'install', 'SIP==4.19.2', 'PyQt5==5.8.2'])
