::
:: Build frozen Tahoe-LAFS on Windows7 (64 bit)
::
::
:: This script assumes that Tahoe-LAFS' build dependencies have already been
:: installed; see/run 'make-tahoe-deps.bat'
::

call git clone https://github.com/tahoe-lafs/tahoe-lafs.git .\build\tahoe-lafs

:: Needed for frozen builds...
call git apply disable_setuptools.patch

:: Workaround for nevow...
call C:\Python27\python.exe -m pip install twisted

call C:\Python27\python.exe -m pip install --upgrade .\build\tahoe-lafs

:: Needed to pass autodeps/init sequence when running frozen...
call C:\Python27\python.exe -m pip install --upgrade twisted
call C:\Python27\python.exe -m pip install --upgrade nevow

call C:\Python27\python.exe -m pip install pyinstaller
set PYTHONHASHSEED=1
set
call C:\Python27\Scripts\pyinstaller.exe --noconfirm tahoe.spec
set PYTHONHASHSEED=
set

echo Done!
