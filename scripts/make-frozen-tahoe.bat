::
:: Build frozen Tahoe-LAFS on Windows7 (64 bit) - virtualenv edition
::
::
:: This script assumes that Tahoe-LAFS' build dependencies have already been
:: installed; see/run 'make-tahoe-deps.bat'
::

call C:\Python27\python.exe -m pip install --upgrade virtualenv
call C:\Python27\python.exe -m virtualenv --clear .\build\venv
call .\build\venv\Scripts\activate

:: This should pull in pywin32 (via pypiwin32)
call pip install --upgrade pyinstaller

:: Build and install pyOpenSSL
call "C:\Users\%USERNAME%\AppData\Local\Programs\Common\Microsoft\Visual C++ for Python\9.0\vcvarsall.bat" x86_amd64
call pushd C:\Users\%USERNAME%\Downloads\pyOpenSSL-0.13.1
call set PYCA_WINDOWS_LINK_TYPE=dynamic
call set LIB=c:\dist\openssl64\lib;%LIB%
call set INCLUDE=c:\dist\openssl64\include;%INCLUDE%
call set PATH=c:\dist\openssl64\bin;%PATH%
call python setup.py build
call python setup.py install
call popd

call git clone https://github.com/tahoe-lafs/tahoe-lafs.git .\build\tahoe-lafs

:: Needed for frozen builds...
call git apply disable_setuptools.patch

call pip install --upgrade .\build\tahoe-lafs

call set PYTHONHASHSEED=1
call pyinstaller --noconfirm tahoe.spec
call python -m zipfile -c dist\Tahoe-LAFS.zip dist\Tahoe-LAFS
call set PYTHONHASHSEED=

call .\build\venv\Scripts\deactivate

echo Done!
