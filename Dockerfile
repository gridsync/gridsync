FROM centos:7

RUN yum -y update && yum -y install \
    gtk3 \
    libicu \
    libxkbcommon-x11 \
    pcre2-utf16 \
    python-cffi \
    xcb-util \
    xcb-util-image \
    xcb-util-keysyms \
    xcb-util-renderutil \
    xcb-util-wm

COPY scripts/provision_devtools.sh /
RUN /provision_devtools.sh && rm /provision_devtools.sh
