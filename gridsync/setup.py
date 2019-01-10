# -*- coding: utf-8 -*-

import base64
import json
import logging as log
import os
import shutil
from binascii import Error

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QInputDialog
import treq
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from gridsync import config_dir, resource, APP_NAME
from gridsync.config import Config
from gridsync.errors import UpgradeRequiredError, TorError
from gridsync.tahoe import Tahoe, select_executable
from gridsync.tor import tor_required, get_tor, get_tor_with_prompt


def is_onion_grid(settings):
    furls = []
    introducer = settings.get('introducer')
    if introducer:
        furls.append(introducer)
    servers = settings.get('storage')
    if servers:
        for data in servers.values():
            if 'anonymous-storage-FURL' in data:
                furls.append(data.get('anonymous-storage-FURL'))
    for furl in furls:
        if tor_required(furl):
            return True
    return False


def prompt_for_grid_name(grid_name, parent=None):
    title = "{} - Choose a name".format(APP_NAME)
    label = "Please choose a name for this connection:"
    if grid_name:
        label = ('{} is already connected to "{}".\n\n'
                 'Please choose a different name for this connection'.format(
                     APP_NAME, grid_name))
    return QInputDialog.getText(parent, title, label, 0, grid_name)


def validate_grid(settings, parent=None):
    nickname = settings.get('nickname')
    while not nickname:
        nickname, _ = prompt_for_grid_name(nickname, parent)
    nodedir = os.path.join(config_dir, nickname)
    if os.path.isdir(nodedir):
        conflicting_introducer = False
        introducer = settings.get('introducer')
        if introducer:
            config = Config(os.path.join(nodedir, 'tahoe.cfg'))
            existing_introducer = config.get('client', 'introducer.furl')
            if introducer != existing_introducer:
                conflicting_introducer = True

        conflicting_servers = False
        servers = settings.get('storage')
        if servers:
            existing_servers = Tahoe(nodedir).get_storage_servers()
            if servers != existing_servers:
                conflicting_servers = True

        if conflicting_introducer or conflicting_servers:
            while os.path.isdir(os.path.join(config_dir, nickname)):
                nickname, _ = prompt_for_grid_name(nickname, parent)
    settings['nickname'] = nickname
    return settings


def prompt_for_folder_name(folder_name, grid_name, parent=None):
    return QInputDialog.getText(
        parent,
        "Folder already exists",
        'You already belong to a folder named "{}" on\n'
        '{}; Please choose a different name.'.format(
            folder_name, grid_name),
        0,
        folder_name
    )


def validate_folders(settings, known_gateways, parent=None):
    gateway = None
    if known_gateways:
        for gw in known_gateways:
            if gw.name == settings['nickname']:
                gateway = gw
    if not gateway:
        return settings
    for folder, data in settings['magic-folders'].copy().items():
        target = folder
        while gateway.magic_folder_exists(target):
            target, ok = prompt_for_folder_name(target, gateway.name, parent)
            if not ok:  # User clicked "Cancel"; skip this folder
                del settings['magic-folders'][folder]
                continue
            if not target:
                target = folder
            elif not gateway.magic_folder_exists(target) and \
                    target not in settings['magic-folders']:
                settings['magic-folders'][target] = data
                del settings['magic-folders'][folder]
    return settings


def validate_settings(settings, known_gateways, parent, from_wormhole=True):
    if from_wormhole and 'rootcap' in settings:
        del settings['rootcap']
    settings = validate_grid(settings, parent)
    if 'magic-folders' in settings:
        settings = validate_folders(settings, known_gateways, parent)
    return settings


class SetupRunner(QObject):

    grid_already_joined = pyqtSignal(str)
    update_progress = pyqtSignal(str)
    client_started = pyqtSignal(object)
    joined_folders = pyqtSignal(list)
    got_icon = pyqtSignal(str)
    done = pyqtSignal(object)

    def __init__(self, known_gateways, use_tor=False):
        super(SetupRunner, self).__init__()
        self.known_gateways = known_gateways
        self.use_tor = use_tor
        self.gateway = None

    def get_gateway(self, introducer, servers):
        if not self.known_gateways:
            return None
        for gateway in self.known_gateways:
            target_introducer = gateway.config_get('client', 'introducer.furl')
            if introducer and introducer == target_introducer:
                return gateway
            target_servers = gateway.get_storage_servers()
            if servers and servers == target_servers:
                return gateway
        return None

    def calculate_total_steps(self, settings):
        steps = 1  # done
        if not self.get_gateway(
                settings.get('introducer'), settings.get('storage')):
            steps += 4  # create, start, await_ready, rootcap
        folders = settings.get('magic-folders')
        if folders:
            steps += len(folders)  # join
        return steps

    def decode_icon(self, s, dest):
        with open(dest, 'wb') as f:
            try:
                f.write(base64.b64decode(s))
            except (Error, TypeError):
                return
        self.got_icon.emit(dest)

    @inlineCallbacks
    def fetch_icon(self, url, dest):
        agent = None
        if self.use_tor:
            tor = yield get_tor(reactor)
            if not tor:
                raise TorError("Could not connect to a running Tor daemon")
            agent = tor.web_agent()
        resp = yield treq.get(url, agent=agent)
        if resp.code == 200:
            content = yield treq.content(resp)
            log.debug("Received %i bytes", len(content))
            with open(dest, 'wb') as f:
                f.write(content)
            self.got_icon.emit(dest)
        else:
            log.warning("Error fetching service icon: %i", resp.code)

    @inlineCallbacks  # noqa: max-complexity=13 XXX
    def join_grid(self, settings):
        nickname = settings['nickname']
        if self.use_tor:
            msg = "Connecting to {} via Tor...".format(nickname)
        else:
            msg = "Connecting to {}...".format(nickname)
        self.update_progress.emit(msg)

        icon_path = None
        if nickname == 'Least Authority S4':
            icon_path = resource('leastauthority.com.icon')
            self.got_icon.emit(icon_path)
        elif 'icon_base64' in settings:
            icon_path = os.path.join(config_dir, '.icon.tmp')
            self.decode_icon(settings['icon_base64'], icon_path)
        elif 'icon_url' in settings:
            # A temporary(?) measure to get around the performance issues
            # observed when transferring a base64-encoded icon through Least
            # Authority's wormhole server. Hopefully this will go away.. See:
            # https://github.com/LeastAuthority/leastauthority.com/issues/539
            log.debug("Fetching service icon from %s...", settings['icon_url'])
            icon_path = os.path.join(config_dir, '.icon.tmp')
            try:
                # It's probably not worth cancelling or holding-up the setup
                # process if fetching/writing the icon fails (particularly
                # if doing so would require the user to get a new invite code)
                # so just log a warning for now if something goes wrong...
                yield self.fetch_icon(settings['icon_url'], icon_path)
            except Exception as e:  # pylint: disable=broad-except
                log.warning("Error fetching service icon: %s", str(e))

        executable = yield select_executable()
        nodedir = os.path.join(config_dir, nickname)
        self.gateway = Tahoe(nodedir, executable=executable)
        yield self.gateway.create_client(**settings)

        if icon_path:
            try:
                shutil.copy(icon_path, os.path.join(nodedir, 'icon'))
            except OSError as err:
                log.warning("Error copying icon file: %s", str(err))
        if 'icon_url' in settings:
            try:
                with open(os.path.join(nodedir, 'icon.url'), 'w') as f:
                    f.write(settings['icon_url'])
            except OSError as err:
                log.warning("Error writing icon url to file: %s", str(err))

        self.update_progress.emit(msg)
        yield self.gateway.start()
        self.client_started.emit(self.gateway)
        self.update_progress.emit(msg)
        yield self.gateway.await_ready()

    @inlineCallbacks
    def ensure_recovery(self, settings):
        settings_path = os.path.join(
            self.gateway.nodedir, 'private', 'settings.json')
        if settings.get('rootcap'):
            self.update_progress.emit('Loading Recovery Key...')
            with open(self.gateway.rootcap_path, 'w') as f:  # XXX
                f.write(settings['rootcap'])
            with open(settings_path, 'w') as f:
                f.write(json.dumps(settings))
        else:
            self.update_progress.emit('Generating Recovery Key...')
            try:
                settings['rootcap'] = yield self.gateway.create_rootcap()
            except OSError:  # XXX Rootcap file already exists
                pass
            with open(settings_path, 'w') as f:
                f.write(json.dumps(settings))
            settings_cap = yield self.gateway.upload(settings_path)
            yield self.gateway.link(
                self.gateway.rootcap, 'settings.json', settings_cap)

    @inlineCallbacks
    def join_folders(self, folders_data):
        folders = []
        for folder, data in folders_data.items():
            self.update_progress.emit('Joining folder "{}"...'.format(folder))
            collective, personal = data['code'].split('+')
            yield self.gateway.link(
                self.gateway.get_rootcap(),
                folder + ' (collective)',
                collective
            )
            yield self.gateway.link(
                self.gateway.get_rootcap(),
                folder + ' (personal)',
                personal
            )
            folders.append(folder)
        if folders:
            self.joined_folders.emit(folders)

    @inlineCallbacks
    def run(self, settings):
        if 'version' in settings and int(settings['version']) > 1:
            raise UpgradeRequiredError

        if self.use_tor or 'hide-ip' in settings or is_onion_grid(settings):
            settings['hide-ip'] = True
            self.use_tor = True
            tor = yield get_tor_with_prompt(reactor)
            if not tor:
                raise TorError("Could not connect to a running Tor daemon")

        self.gateway = self.get_gateway(
            settings.get('introducer'), settings.get('storage')
        )
        folders_data = settings.get('magic-folders')
        if not self.gateway:
            yield self.join_grid(settings)
        elif not folders_data:
            self.grid_already_joined.emit(settings.get('nickname'))

        yield self.ensure_recovery(settings)

        if folders_data:
            yield self.join_folders(folders_data)

        self.update_progress.emit('Done!')
        self.done.emit(self.gateway)
