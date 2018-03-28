# -*- coding: utf-8 -*-

import base64
import json
import logging as log
import os
import shutil
from binascii import Error

from PyQt5.QtCore import pyqtSignal, QObject
import treq
from twisted.internet.defer import inlineCallbacks

from gridsync import config_dir, resource
from gridsync.errors import UpgradeRequiredError
from gridsync.tahoe import Tahoe, select_executable


class SetupRunner(QObject):

    grid_already_joined = pyqtSignal(str)
    update_progress = pyqtSignal(str)
    joined_folders = pyqtSignal(list)
    got_icon = pyqtSignal(str)
    done = pyqtSignal(object)

    def __init__(self, known_gateways):
        super(SetupRunner, self).__init__()
        self.known_gateways = known_gateways
        self.gateway = None

    def get_gateway(self, introducer):
        if not introducer or not self.known_gateways:
            return None
        for gateway in self.known_gateways:
            if gateway.config_get('client', 'introducer.furl') == introducer:
                return gateway
        return None

    def calculate_total_steps(self, settings):
        steps = 1  # done
        if not self.get_gateway(settings.get('introducer')):
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
        resp = yield treq.get(url)
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
        if 'nickname' in settings:
            nickname = settings['nickname']
        else:
            nickname = settings['introducer'].split('@')[1].split(':')[0]

        self.update_progress.emit('Connecting to {}...'.format(nickname))
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
                yield self.fetch_service_icon(settings['icon_url'], icon_path)
            except Exception as e:  # pylint: disable=broad-except
                log.warning("Error fetching service icon: %s", str(e))

        executable, multi_folder_support = yield select_executable()
        nodedir = os.path.join(config_dir, nickname)
        self.gateway = Tahoe(
            nodedir,
            executable=executable,
            multi_folder_support=multi_folder_support
        )
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

        self.update_progress.emit('Connecting to {}...'.format(nickname))
        yield self.gateway.start()

        self.update_progress.emit('Connecting to {}...'.format(nickname))
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

        self.gateway = self.get_gateway(settings.get('introducer'))
        if not self.gateway:
            yield self.join_grid(settings)
        else:
            self.grid_already_joined.emit(settings.get('nickname'))

        yield self.ensure_recovery(settings)

        folders_data = settings.get('magic-folders')
        if folders_data:
            yield self.join_folders(folders_data)

        self.update_progress.emit('Done!')
        self.done.emit(self.gateway)
