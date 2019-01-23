import platform
import subprocess
import sys


version = platform.mac_ver()[0]

if not version:
    sys.exit("Not a Mac or no version detected; exiting")

major = int(version.split('.')[0])
minor = int(version.split('.')[1])

# Newer (5.9+?) versions of (Py)Qt5 are incompatible with older Macs and will
# fail with "Symbol not found: _LSCopyDefaultApplicationURLForURL" on Mac OS X
# 10.9. Downgrading SIP to 4.19.2 and PyQt5 to 5.8.2 avoids this error..
if (major, minor) < (10, 10):
    print("Older Mac detected ({}); "
          "Downgrading SIP, PyQt5...".format(version))
    subprocess.call([
        'python', '-m', 'pip', 'install', 'SIP==4.19.2', 'PyQt5==5.8.2'])
# As of version 5.11, a "private" SIP module is provided by PyQt5, replacing
# the standalone "SIP" library. Unfortunately, py2app seems unable to detect
# the vendored version, so install the standalone SIP 4.19.8 library for now.
# See https://www.riverbankcomputing.com/pipermail/pyqt/2018-June/040421.html
else:
    subprocess.call(['python', '-m', 'pip', 'install', 'SIP==4.19.8'])
