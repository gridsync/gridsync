FROM centos:7

RUN yum -y update && yum -y install \
    # Seemingly required by Gridsync/Qt5, as per scripts/get_yum_packages.py; also provided by GNOME Desktop:
    gtk3 libicu libxkbcommon-x11 pcre2-utf16 python-cffi xcb-util xcb-util-image xcb-util-keysyms xcb-util-renderutil xcb-util-wm \
    # Required for pyenv, tests, build process; from scripts/provision_devtools.sh:
    which make gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel xz git xorg-x11-server-Xvfb file \
    && yum clean all

RUN git clone https://github.com/pyenv/pyenv.git ~/.pyenv \
    && echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile \
    && echo 'export PATH="$PYENV_ROOT/bin:$HOME/bin:$PATH"' >> ~/.bash_profile \
    && echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bash_profile \
    && source ~/.bash_profile \
    && export PYTHON_CONFIGURE_OPTS="--enable-shared" \
    && pyenv install 2.7.18 \
    && pyenv install 3.8.7 \
    && pyenv rehash \
    && pyenv global 2.7.18 3.8.7 \
    && python2 -m pip install --upgrade setuptools pip \
    && python3 -m pip install --upgrade setuptools pip tox && env

RUN curl --proto '=https' -sSf https://sh.rustup.rs > /usr/bin/rustup-init \
    && chmod +x /usr/bin/rustup-init \
    && rustup-init -y --default-host x86_64-unknown-linux-gnu --default-toolchain stable

RUN curl -fsSL --create-dirs -o /usr/bin/linuxdeploy https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage \
    && chmod +x /usr/bin/linuxdeploy

RUN curl -fsSL --create-dirs -o /usr/bin/appimagetool https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage \
    && chmod +x /usr/bin/appimagetool

CMD ["bash", "-l", "-c", "make"]
