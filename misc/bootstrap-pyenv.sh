#!/bin/sh

# Debian/Ubuntu
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev git

# Fedora 22+
#sudo dnf install -y make gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel xz git

git clone https://github.com/pyenv/pyenv.git ~/.pyenv

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bashrc
exec "$SHELL"

env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 2.7.15
env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.5.6
env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.6.8
env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.7.2

pyenv rehash
pyenv global 2.7.15 3.6.8 3.5.6 3.7.2
