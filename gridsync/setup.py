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
from gridsync.tahoe import Tahoe


class Setup(QObject):

    update_progress = pyqtSignal(int, str)
    got_icon = pyqtSignal(str)
    done = pyqtSignal(object)

    def __init__(self, parent=None):
        super(Setup, self).__init__()
        self.parent = parent

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
    def run(self, settings):
        if 'version' in settings and int(settings['version']) > 1:
            raise UpgradeRequiredError

        if 'nickname' in settings:
            nickname = settings['nickname']
        else:
            nickname = settings['introducer'].split('@')[1].split(':')[0]

        self.update_progress.emit(2, 'Connecting to {}...'.format(nickname))
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
        tahoe = Tahoe(os.path.join(config_dir, nickname))
        yield tahoe.create_client(**settings)
        if icon_path:
            try:
                shutil.copy(icon_path, os.path.join(tahoe.nodedir, 'icon'))
            except OSError as err:
                log.warning("Error copying icon file: %s", str(err))
        if 'icon_url' in settings:
            try:
                with open(os.path.join(tahoe.nodedir, 'icon.url'), 'w') as f:
                    f.write(settings['icon_url'])
            except OSError as err:
                log.warning("Error writing icon url to file: %s", str(err))

        self.update_progress.emit(3, 'Connecting to {}...'.format(nickname))
        yield tahoe.start()

        self.update_progress.emit(4, 'Connecting to {}...'.format(nickname))
        yield tahoe.await_ready()

        if 'rootcap' in settings:
            self.update_progress.emit(5, 'Loading Recovery Key...')
            with open(tahoe.rootcap_path, 'w') as f:  # XXX
                f.write(settings['rootcap'])
        else:
            self.update_progress.emit(5, 'Generating Recovery Key...')
            yield tahoe.create_rootcap()
        settings_json = os.path.join(tahoe.nodedir, 'private', 'settings.json')
        with open(settings_json, 'w') as f:
            f.write(json.dumps(settings))
        # TODO: Upload, link to rootcap

        self.update_progress.emit(6, 'Done!')
        self.done.emit(tahoe)
