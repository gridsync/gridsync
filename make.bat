::
:: This script assumes that the following dependencies have been installed:
::
::  1) Git <https://git-scm.com/download/win>
::
::  2) Python 2.7 <https://www.python.org>
::
::  3) Python 3.7 <https://www.python.org>
::      -Select "Add Python 3.7 to PATH" option during install
::      -On Windows Server 2012, if installation fails, try installing update "KB2919355". See https://bugs.python.org/issue29583
::
::  4) Microsoft Visual C++ Compiler for Python 2.7 <https://aka.ms/vcpython27>
::
::  5) Microsoft .NET Framework Dev Pack <https://aka.ms/dotnet-download>
::
::  6) Microsoft Visual C++ Build Tools 2015 <https://aka.ms/buildtools>
::      -Select "Windows 8.1 SDK" and "Windows 10 SDK" options during install
::
::  7) Inno Setup <http://www.jrsoftware.org/isinfo.php>
::

@echo off

if defined APPVEYOR (
    if "%PYTHON_ARCH%" == "64" (
        set PYTHON2=C:\Python27-x64\python.exe
    ) else (
        set PYTHON2=C:\Python27\python.exe
    )
    set PYTHON3=%PYTHON%\python.exe
) else (
    set PYTHON2=py -2.7
    set PYTHON3=py -3
)

if "%1"=="clean" call :clean
if "%1"=="test" call :test
if "%1"=="frozen-tahoe" call :frozen-tahoe
if "%1"=="pyinstaller" call :pyinstaller
if "%1"=="zip" call :zip
if "%1"=="test-determinism" call :test-determinism
if "%1"=="installer" call :installer
if "%1"=="vagrant-build-linux" call :vagrant-build-linux
if "%1"=="vagrant-build-macos" call :vagrant-build-macos
if "%1"=="vagrant-build-windows" call :vagrant-build-windows
if "%1"=="all" call :all
if "%1"=="" call :all
goto :eof

:clean
rmdir /s /q .\build
rmdir /s /q .\dist
rmdir /s /q .\.eggs
rmdir /s /q .\.cache
rmdir /s /q .\.tox
rmdir /s /q .\htmlcov
rmdir /s /q .\.pytest_cache
rmdir /s /q .\.mypy_cache
del .\.coverage
goto :eof

:test
%PYTHON3% -m tox || exit %ERRORLEVEL%
goto :eof

:frozen-tahoe
%PYTHON2% -m pip install --upgrade setuptools pip virtualenv
%PYTHON2% -m virtualenv --clear .\build\venv-tahoe
.\build\venv-tahoe\Scripts\activate
python -m pip install --upgrade setuptools pip
git clone https://github.com/tahoe-lafs/tahoe-lafs.git .\build\tahoe-lafs
pushd .\build\tahoe-lafs
git checkout tahoe-lafs-1.14.0
copy ..\..\misc\storage_client.py.patch .
git apply --ignore-space-change --ignore-whitespace storage_client.py.patch
copy ..\..\misc\rsa-public-exponent.patch .
git apply --ignore-space-change --ignore-whitespace rsa-public-exponent.patch
python setup.py update_version
python -m pip install -r ..\..\requirements\tahoe-lafs.txt
git clone https://github.com/PrivateStorageio/ZKAPAuthorizer .\build\ZKAPAuthorizer
copy ..\..\misc\zkapauthorizer-retry-interval.patch .\build\ZKAPAuthorizer
pushd .\build\ZKAPAuthorizer
git checkout 632d2cdc96bb2975d8aff573a3858f1a6aae9963
git apply --ignore-space-change --ignore-whitespace zkapauthorizer-retry-interval.patch
python -m pip install .
popd
python -m pip install .
python -m pip install -r ..\..\requirements\pyinstaller.txt
python -m pip list
copy ..\..\misc\tahoe.spec pyinstaller.spec
set PYTHONHASHSEED=1
pyinstaller pyinstaller.spec
set PYTHONHASHSEED=
mkdir dist\Tahoe-LAFS\challenge_bypass_ristretto
copy ..\venv-tahoe\Lib\site-packages\challenge_bypass_ristretto\*.pyd dist\Tahoe-LAFS\challenge_bypass_ristretto\
move dist ..\..
popd
deactivate
goto :eof

:pyinstaller
if not exist ".\dist\Tahoe-LAFS" call :frozen-tahoe
%PYTHON3% -m tox -e pyinstaller || exit /b 1
goto :eof

:zip
%PYTHON3% .\scripts\update_permissions.py .\dist
%PYTHON3% .\scripts\update_timestamps.py .\dist
%PYTHON3% .\scripts\make_zip.py
goto :eof

:test-determinism
%PYTHON3% .\scripts\test_determinism.py
goto :eof

:installer
%PYTHON3% .\scripts\make_installer.py
goto :eof


:vagrant-build-linux
vagrant up centos-7
vagrant provision --provision-with devtools,test,build centos-7
goto :eof

:vagrant-build-macos
vagrant up --provision-with devtools,test,build macos-10.14
goto :eof

:vagrant-build-windows
call vagrant up --provision-with devtools,test,build windows-10
goto :eof


:all
call :pyinstaller
call :zip
call :installer
call %PYTHON3% .\scripts\sha256sum.py .\dist\*.*
goto :eof

:error
echo ERRORR %errorlevel%
echo ERRORR %errorlevel%
exit %errorlevel%
