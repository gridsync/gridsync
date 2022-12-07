choco install -y --no-progress --require-checksums git
choco install -y --no-progress --require-checksums -m python3 --version 3.9.13
choco install -y --no-progress --require-checksums -m python3 --version 3.10.6
choco install -y --no-progress --require-checksums visualcpp-build-tools
choco install -y --no-progress --require-checksums innosetup
refreshenv
:: Tox 4.0.0 is not passing environment variables down to package/build/install
:: stages, breaking our current handling of environment variables in setup.py.
:: See/follow https://github.com/tox-dev/tox/issues/2543
py -3 -m pip install --upgrade setuptools pip 'tox<4' diffoscope
git config --global core.autocrlf false
reg add "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled /t REG_DWORD /d 1 /f
