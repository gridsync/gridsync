FROM centos:7

RUN yum -y update && yum -y install \
    # Seemingly required by Gridsync/Qt5, as per scripts/get_yum_packages.py; also provided by GNOME Desktop:
    gtk3 libicu libxkbcommon-x11 pcre2-utf16 python-cffi xcb-util xcb-util-image xcb-util-keysyms xcb-util-renderutil xcb-util-wm \
    && yum clean all

COPY scripts/provision_devtools.sh /
RUN SKIP_DOCKER_INSTALL=1 SKIP_OLD_PYTHON_VERSIONS=1 /provision_devtools.sh && rm /provision_devtools.sh

WORKDIR /gridsync
CMD ["bash", "-l", "-c", "make"]
