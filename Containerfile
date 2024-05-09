FROM docker.io/library/almalinux:8

RUN dnf install -y 'dnf-command(config-manager)' && dnf config-manager --set-enabled powertools && dnf install -y epel-release && yum -y update && yum -y install \
    findutils gtk3 libicu libxkbcommon-x11 mesa-libEGL pcre2-utf16 xcb-util xcb-util-image xcb-util-keysyms xcb-util-renderutil xcb-util-wm xcb-util-cursor \
    && yum clean all

COPY scripts/provision_devtools.sh /
RUN SKIP_DOCKER_INSTALL=1 /provision_devtools.sh && rm /provision_devtools.sh

WORKDIR /gridsync
CMD ["bash", "-l", "-c", "make"]
