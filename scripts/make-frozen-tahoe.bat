::
:: Build frozen Tahoe-LAFS on Windows7 (64 bit) - virtualenv edition
::
::
:: This script assumes that Tahoe-LAFS' build dependencies have already been
:: installed; see/run 'make-tahoe-deps.bat'
::

call pip install --upgrade virtualenv
call virtualenv --clear .\build\venv
call .\build\venv\Scripts\activate

call git clone https://github.com/tahoe-lafs/tahoe-lafs.git .\build\tahoe-lafs

:: Needed for frozen builds...
call git apply disable_setuptools.patch

:: Workaround for Nevow-0.10.0 requiring twisted.python when Twisted 12.1 is pinned..
call pip install --upgrade twisted

call pip install --upgrade .\build\tahoe-lafs

call pip install --upgrade pyinstaller
set PYTHONHASHSEED=1
call pyinstaller --noconfirm tahoe.spec
call python -m zipfile -c dist\Tahoe-LAFS.zip dist\Tahoe-LAFS
set PYTHONHASHSEED=

call .\build\venv\Scripts\deactivate
echo Done!
