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

:: Workaround for Nevow-0.10.0 requiring twisted.python when Twisted 12.1 is pinned ("Collecting Nevow<=0.10,>=0.9.33 [...] ImportError: No module named twisted.python")
call pip install --upgrade twisted

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

call pip install --upgrade .\build\tahoe-lafs

:: Needed to pass autodeps/init sequence when running frozen ("PackagingError: We require Twisted >= 13.0.0, but could only find version 12.1.0.")
call pip install --upgrade twisted

:: Same as above ("PackagingError: We require Nevow >= 0.11.1, but could only find version 0.10.0.")
call pip install --upgrade nevow

call pip install --upgrade pyinstaller
call set PYTHONHASHSEED=1
call pyinstaller --noconfirm tahoe.spec
call python -m zipfile -c dist\Tahoe-LAFS.zip dist\Tahoe-LAFS
call set PYTHONHASHSEED=

call .\build\venv\Scripts\deactivate

echo Done!
