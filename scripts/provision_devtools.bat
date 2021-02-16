choco install -y --no-progress --require-checksums git
choco install -y --no-progress --require-checksums python2
choco install -y --no-progress --require-checksums vcpython27
choco install -y --no-progress --require-checksums -m python3 --version 3.8.7
choco install -y --no-progress --require-checksums -m python3 --version 3.7.9
choco install -y --no-progress --require-checksums -m python3 --version 3.6.8
choco install -y --no-progress --require-checksums visualcpp-build-tools
choco install -y --no-progress --require-checksums innosetup
choco install -y --no-progress --require-checksums rust-ms
py -2 -m pip install --upgrade setuptools pip
py -3 -m pip install --upgrade setuptools pip tox
