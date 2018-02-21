import platform
import subprocess
import sys


version = platform.mac_ver()[0]

if not version:
    sys.exit("Not a Mac or no version detected; exiting")

major = int(version.split('.')[0])
minor = int(version.split('.')[1])

if (major, minor) < (10, 10):
    print("Older Mac detected ({}); "
          "Rebuilding libsodium/PyNaCl...".format(version))
    subprocess.call(['pip', 'install', '--ignore-installed', '--no-deps',
                     '--no-binary', 'PyNaCl', 'PyNaCl==1.2.1'])
