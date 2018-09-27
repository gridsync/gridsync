import platform
import subprocess
import sys


version = platform.mac_ver()[0]

if not version:
    sys.exit("Not a Mac or no version detected; exiting")

major = int(version.split('.')[0])
minor = int(version.split('.')[1])

# The precompiled libsodium library included with PyNaCl wheels crashes with
# "EXC_BAD_INSTRUCTION (SIGILL)" on some older (2007 era? OS X 10.9?) Macs.
# Recompling libsodium/PyNaCl from source on such older systems avoids this.
if (major, minor) < (10, 10):
    print("Older Mac detected ({}); "
          "Rebuilding libsodium/PyNaCl...".format(version))
    # XXX Keep pinned to 1.2.1 for now; version 1.3.0 raises "AttributeError:
    # cffi library '_sodium' has no function, constant or global variable named
    # 'crypto_aead_chacha20poly1305_ietf_keybytes'"
    subprocess.call(['pip', 'install', '--force-reinstall', '--no-deps',
                     '--no-binary', 'PyNaCl', 'PyNaCl==1.2.1'])
