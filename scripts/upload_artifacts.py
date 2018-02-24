from __future__ import print_function

import os
import shutil
import subprocess
import sys
import time


print("Uploading artifacts to storage grid...")

try:
    introducer = os.environ['TAHOE_INTRODUCER_FURL']
except KeyError:
    sys.exit("TAHOE_INTRODUCER_FURL not set; exiting")

files = sys.argv[1:]
if not files:
    sys.exit("No files to upload; exiting")

subprocess.check_output([
    'dist/Tahoe-LAFS/tahoe',
    'create-client',
    '-i', introducer,
    '--shares-happy=1',
    '--shares-needed=1',
    '--shares-total=1',
    '--webport=tcp:0',
    '.tahoe'
])
subprocess.check_output(['dist/Tahoe-LAFS/tahoe', '-d', '.tahoe', 'start'])
time.sleep(3)

for path in files:
    if os.path.isfile(path):
        output = subprocess.check_output(
            ['dist/Tahoe-LAFS/tahoe', '-d', '.tahoe', 'put', path],
            stderr=subprocess.STDOUT
        )
        resp, cap = output.decode().strip().split('\n')
        if resp == '200 OK':
            print(cap, path)

subprocess.check_output(['dist/Tahoe-LAFS/tahoe', '-d', '.tahoe', 'stop'])
shutil.rmtree('.tahoe')
print("Done!")
