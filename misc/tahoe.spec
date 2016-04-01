# -*- mode: python -*-

from distutils.sysconfig import get_python_lib
import os
import shutil
import sys

if not hasattr(sys, 'real_prefix'):
    sys.exit("Please run inside a virtualenv with Tahoe-LAFS installed.")

# XXX: Ugly hack to disable tahoe's setuptools check. Needed for frozen builds.
try:
    auto_deps = os.path.join(get_python_lib(), 'allmydata', '_auto_deps.py')
    shutil.copy2(auto_deps, '_auto_deps.py.original')
    with open(auto_deps) as f, open('_auto_deps.py.modified', 'w+') as n:
        n.write(f.read().replace('"setuptools >=', '#"setuptools >='))
    shutil.move('_auto_deps.py.modified', auto_deps)
except Exception as e:
    sys.exit(e)

options = [('u', None, 'OPTION')]

added_files = [
    ('src/allmydata/web/*.xhtml', 'allmydata/web'),
    ('src/allmydata/web/static/*', 'allmydata/web/static'),
    ('src/allmydata/web/static/css/*', 'allmydata/web/static/css'),
    ('src/allmydata/web/static/img/*.png', 'allmydata/web/static/img')]

a = Analysis(['static/tahoe.py'],
             pathex=[],
             binaries=None,
             datas=added_files,
             hiddenimports=['characteristic', 'cffi'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=None)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(pyz,
          a.scripts,
          options,
          exclude_binaries=True,
          name='tahoe',
          debug=False,
          strip=False,
          upx=False,
          console=True)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='Tahoe-LAFS')

try:
    shutil.move('_auto_deps.py.original', auto_deps)
except Exception as e: 
    sys.exit(e)
