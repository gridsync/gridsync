# -*- mode: python -*-

from __future__ import print_function

from distutils.sysconfig import get_python_lib
import sys


# https://github.com/pyinstaller/pyinstaller/wiki/Recipe-remove-tkinter-tcl
sys.modules['FixTk'] = None

options = [
    # Enable unbuffered stdio:
    ('u', None, 'OPTION'),
    # Supress CryptographyDeprecationWarning (https://github.com/gridsync/gridsync/issues/313):
    ('W ignore::UserWarning', None, 'OPTION')
]

added_files = [
    ('COPYING.*', '.'),
    ('CREDITS', '.'),
    ('relnotes.txt', '.'),
    ('src/allmydata/web/*.xhtml', 'allmydata/web'),
    ('src/allmydata/web/static/*', 'allmydata/web/static'),
    ('src/allmydata/web/static/css/*', 'allmydata/web/static/css'),
    ('src/allmydata/web/static/img/*.png', 'allmydata/web/static/img')]

hidden_imports = [
    '__builtin__',
    'allmydata.client',
    'allmydata.introducer',
    'allmydata.stats',
    'base64',
    'cffi',
    'collections',
    'commands',                                                                
    'Crypto',                                                                  
    'functools',                                                               
    'future.backports.misc',                                                   
    'itertools',                                                               
    'math',                                                                    
    'packaging.specifiers',                                                    
    're',                                                                      
    'reprlib',                                                                 
    'six.moves.html_parser',                                                   
    'subprocess',                                                              
    'UserDict',
    'UserList',
    'UserString',
    'yaml',
    'zfec',
]

a = Analysis(
    ['static/tahoe.py'],
    pathex=[],
    binaries=None,
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    options,
    exclude_binaries=True,
    name='tahoe',
    debug=False,
    strip=False,
    upx=False,
    console=True)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='Tahoe-LAFS')
