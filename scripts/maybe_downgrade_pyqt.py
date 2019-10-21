import platform
import subprocess
import sys


if sys.platform == 'darwin':
    version = platform.mac_ver()[0]
    major = int(version.split('.')[0])
    minor = int(version.split('.')[1])
    if (major, minor) < (10, 12):
        print("Older Mac detected ({}); Downgrading SIP, PyQt5...".format(
            version))
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
                'python', '-m', 'pip', 'install', 'SIP==4.19.2',
                'PyQt5==5.8.2'])
elif sys.platform == 'linux':
    #version = platform.dist()[1]
    version = ''
    if version.startswith('jessie') or version.startswith('8.'):
        print("Older Linux distro detected ({}); Downgrading SIP, PyQt5..."
              .format(version))
        # PyQt5 5.12 fails on Debian 8/Jessie, Ubuntu 14.04: "libQt5DBus.so.5:
        # symbol dbus_message_get_allow_interactive_authorization, version
        # LIBDBUS_1_3 not defined in file libdbus-1.so.3 with link time
        # reference" as well as "libQt5XcbQpa.so.5: undefined symbol:
        # FT_Get_Font_Format"
        subprocess.call([
            'python', '-m', 'pip', 'install', 'PyQt5==5.11.3',
            'PyQt5-sip==4.19.13'])
