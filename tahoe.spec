# -*- mode: python -*-

options = [('u', None, 'OPTION')]

block_cipher = None

added_files = [
    ('build/tahoe-lafs/src/allmydata/web/*.xhtml', 'allmydata/web'),
    ('build/tahoe-lafs/src/allmydata/web/static/*', 'allmydata/web/static'),
    ('build/tahoe-lafs/src/allmydata/web/static/css/*', 'allmydata/web/static/css'),
    ('build/tahoe-lafs/src/allmydata/web/static/img/*', 'allmydata/web/static/img')]

a = Analysis(['build/tahoe-lafs/static/tahoe.py'],
             pathex=[],
             binaries=None,
             datas=added_files,
             hiddenimports=['characteristic', 'pyasn1_modules'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          options,
          exclude_binaries=True,
          name='tahoe',
          debug=True,
          strip=False,
          upx=False,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='Tahoe-LAFS')
