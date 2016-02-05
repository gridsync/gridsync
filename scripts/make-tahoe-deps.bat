::
:: Build Tahoe-LAFS dependencies on Windows7 (64 bit)
::
:: Adapted from https://github.com/tahoe-lafs/tahoe-lafs/blob/195.windows-packaging.10/docs/build/windows-installer.rst
::
::
:: This script assumes that the following dependencies have already been 
:: downloaded and properly installed:
::
::      Python 2.7: https://www.python.org/
::      Microsoft Visual C++ Compiler for Python 2.7: https://www.microsoft.com/en-us/download/details.aspx?id=44266
::      ActiveState Perl: https://www.activestate.com/activeperl/downloads
::      Git: https://git-scm.com/download/win
::
::
:: The following source packages must also be downloaded and unpacked (to 
:: C:\Users\%USERNAME%\Downloads in this case):
::
::      OpenSSL (version 1.0.2f at the time of writing): https://www.openssl.org/source/
::      pyOpenSSL 0.13.1: https://pypi.python.org/pypi/pyOpenSSL/0.13.1
::
::
:: Lastly, in the event of a missing 'vcvarsall.bat' error, change line 266
:: in Python27\Lib\distutils\msvc9compiler.py to point directly to the file,
:: e.g.:
::
::      vcvarsall = "C:/Users/Buildbot/AppData/Local/Programs/Common/Microsoft/Visual C++ for Python/9.0/vcvarsall.bat"
::

call cd C:\Users\%USERNAME%\Downloads

:: Build OpenSSL
call "C:\Users\%USERNAME%\AppData\Local\Programs\Common\Microsoft\Visual C++ for Python\9.0\vcvarsall.bat" amd64
call cd openssl-1.0.2f
call mkdir c:\dist
call perl Configure VC-WIN64A --prefix=c:\dist\openssl64 no-asm enable-tlsext
call ms\do_win64a.bat
call nmake -f ms\ntdll.mak
call nmake -f ms\ntdll.mak install
call cd ..

:: Build pyOpenSSL
call "C:\Users\%USERNAME%\AppData\Local\Programs\Common\Microsoft\Visual C++ for Python\9.0\vcvarsall.bat" x86_amd64
call cd pyOpenSSL-0.13.1
call set PYCA_WINDOWS_LINK_TYPE=dynamic
call set LIB=c:\dist\openssl64\lib;%LIB%
call set INCLUDE=c:\dist\openssl64\include;%INCLUDE%
call set PATH=c:\dist\openssl64\bin;%PATH%
call C:\Python27\python.exe setup.py build
call C:\Python27\python.exe setup.py install
call cd ..

echo Done!
