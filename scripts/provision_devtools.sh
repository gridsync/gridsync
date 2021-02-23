#!/bin/sh

if [ "$(uname)" = "Darwin" ]; then
    export HOMEBREW_NO_ANALYTICS=1
    if [ ! -f "/usr/local/bin/brew" ]; then
        yes | /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
    fi
    brew -v analytics off
    brew install openssl readline sqlite3 xz zlib rustup-init
    export MACOSX_DEPLOYMENT_TARGET="10.13"
    export PYTHON_CONFIGURE_OPTS="--enable-framework"
    export RUST_DEFAULT_HOST="x86_64-apple-darwin"
    SHELLRC=~/.$(basename "$SHELL"rc)
else
    if [ -f "/usr/bin/apt-get" ]; then
        sudo apt-get -y update
        sudo apt-get -y install --no-install-recommends make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev git xvfb libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-xinerama0 libgl1 libgl1-mesa-dev x11-utils libdbus-1-3 libxcb-xfixes0
        SHELLRC=~/.bash_profile
    elif [ -f "/usr/bin/yum" ]; then
        PKGS="which make gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel xz git xorg-x11-server-Xvfb file"
        yum -y install $PKGS || sudo yum -y install $PKGS
        SHELLRC=~/.bashrc
	    ECHO_FLAGS=-e
    else
        echo "Error: Unknown environment"
        exit 1
    fi
    export PYTHON_CONFIGURE_OPTS="--enable-shared"
    export RUST_DEFAULT_HOST="x86_64-unknown-linux-gnu"
    curl -fsSL --create-dirs -o ~/bin/linuxdeploy https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
    chmod +x ~/bin/linuxdeploy
    curl -fsSL --create-dirs -o ~/bin/appimagetool https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x ~/bin/appimagetool
    curl --proto '=https' -sSf https://sh.rustup.rs > ~/bin/rustup-init
    chmod +x ~/bin/rustup-init
fi

git clone https://github.com/pyenv/pyenv.git ~/.pyenv || git --git-dir=$HOME/.pyenv/.git pull --ff origin master
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> "$SHELLRC"
echo 'export PATH="$PYENV_ROOT/bin:$HOME/bin:$PATH"' >> "$SHELLRC"
echo "$ECHO_FLAGS" 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> "$SHELLRC"

. "$SHELLRC"

pyenv install --skip-existing 2.7.18
pyenv install --skip-existing 3.8.7

if [[ "${SKIP_OLD_PYTHON_VERSIONS}" ]]; then
    echo "Skipping old python versions"
    pyenv rehash
    pyenv global 2.7.18 3.8.7
else
    pyenv install --skip-existing 3.7.9
    # Python 3.6 is now in "security fixes only"[0] mode and won't build on macOS
    # 10.16/11/"Big Sur" without backporting patches[1][2] -- in other words, it
    # isn't supported "officially" upstream. Because of this -- and because it's
    # more important to support a new version of macOS than an old version of
    # Python -- in the event that the Python 3.6 build fails, continue anyway.
    # [0] https://www.python.org/dev/peps/pep-0494/
    # [1] https://github.com/pyenv/pyenv/issues/1737
    # [2] https://github.com/pyenv/pyenv/issues/1746
    pyenv install --skip-existing 3.6.12 || true
    pyenv rehash
    pyenv global 2.7.18 3.8.7 3.7.9 3.6.12 || pyenv global 2.7.18 3.8.7 3.7.9
fi

python2 -m pip install --upgrade setuptools pip
python3 -m pip install --upgrade setuptools pip tox

rustup-init -y --default-host "$RUST_DEFAULT_HOST" --default-toolchain stable
. $HOME/.cargo/env
