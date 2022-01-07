:: This script assumes that the dependencies listed in
:: scripts/provision_devtools.bat have already been installed.

@echo off

:: Tahoe-LAFS' `zfec` and `netifaces` dependencies currently do not provide
:: binary wheels for CPython 3.9 (or later) so, for now, use 3.8 to avoid
:: building C extensions -- and to keep PyInstaller builds deterministic.
set PYTHON3=py -3.9
set CL=/Brepro
::set LINK=/Brepro


if "%1"=="clean" call :clean
if "%1"=="test" call :test
if "%1"=="test-integration" call :test-integration
if "%1"=="frozen-tahoe" call :frozen-tahoe
if "%1"=="magic-folder" call :magic-folder
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
call rmdir /s /q .\build
call rmdir /s /q .\dist
call rmdir /s /q .\.eggs
call rmdir /s /q .\.cache
call rmdir /s /q .\.tox
call rmdir /s /q .\htmlcov
call rmdir /s /q .\.pytest_cache
call rmdir /s /q .\.mypy_cache
call del .\.coverage
goto :eof

:test
%PYTHON3% -m tox || goto :error
goto :eof

:test-integration
%PYTHON3% -m tox -e integration || goto :error
goto :eof

:frozen-tahoe
call %PYTHON3% -m pip install --upgrade setuptools pip virtualenv
call %PYTHON3% -m virtualenv --clear .\build\venv-tahoe
call .\build\venv-tahoe\Scripts\activate
call python -m pip install --upgrade setuptools pip
call python .\scripts\reproducible-pip.py install git+https://github.com/PrivateStorageio/ZKAPAuthorizer@python3
call python -m pip install -r requirements\pyinstaller.txt
call python -m pip list
call set PYTHONHASHSEED=1
call pyinstaller -y misc/tahoe.spec || goto :error
call set PYTHONHASHSEED=
call popd
call deactivate
goto :eof

:magic-folder
::call %PYTHON3% scripts/checkout-github-repo requirements/magic-folder.json build/magic-folder
call git clone -b python3-support.2 https://github.com/meejah/magic-folder build\magic-folder
call %PYTHON3% -m virtualenv --clear build\venv-magic-folder
call .\build\venv-magic-folder\Scripts\activate
call python -m pip install -r requirements\pyinstaller.txt
call copy misc\magic-folder.spec build\magic-folder
call pushd build\magic-folder
call python ..\..\scripts\reproducible-pip.py install --require-hashes -r requirements\base.txt
call python -m pip install --no-deps .
call python -m pip list
call set PYTHONHASHSEED=1
call python -m PyInstaller magic-folder.spec || goto :error
call set PYTHONHASHSEED=
call popd
call move build\magic-folder\dist\magic-folder dist
call deactivate
goto :eof

:pyinstaller
if not exist ".\dist\Tahoe-LAFS" call :frozen-tahoe
if not exist ".\dist\magic-folder" call :magic-folder
%PYTHON3% -m tox -e pyinstaller || goto :error
goto :eof

:zip
%PYTHON3% .\scripts\update_permissions.py .\dist || goto :error
%PYTHON3% .\scripts\update_timestamps.py .\dist || goto :error
%PYTHON3% .\scripts\make_zip.py || goto :error
goto :eof

:test-determinism
%PYTHON3% .\scripts\test_determinism.py || goto :error
goto :eof

:installer
call %PYTHON3% .\scripts\make_installer.py || goto :error
goto :eof


:vagrant-build-linux
call vagrant up centos-7
call vagrant provision --provision-with devtools,test,build centos-7
goto :eof

:vagrant-build-macos
call vagrant up --provision-with devtools,test,build macos-10.14
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
echo Error in batch file; exiting with error level %errorlevel%
exit %errorlevel%
