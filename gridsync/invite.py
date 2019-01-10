# -*- coding: utf-8 -*-

import json
import os

from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtCore import QObject
from twisted.internet.defer import DeferredList, inlineCallbacks
try:
    from wormhole.wordlist import raw_words
except ImportError:  # TODO: Switch to new magic-wormhole completion API?
    from wormhole._wordlist import raw_words

from gridsync import pkgdir
from gridsync.setup import SetupRunner, validate_settings
from gridsync.util import b58encode
from gridsync.wormhole_ import Wormhole


cheatcodes = []
try:
    for file in os.listdir(os.path.join(pkgdir, 'resources', 'providers')):
        cheatcodes.append(file.split('.')[0].lower())
except OSError:
    pass


wordlist = []
for word in raw_words.items():
    wordlist.extend(word[1])
for c in cheatcodes:
    wordlist.extend(c.split('-'))
wordlist = sorted([word.lower() for word in wordlist])


def load_settings_from_cheatcode(cheatcode):
    path = os.path.join(pkgdir, 'resources', 'providers', cheatcode + '.json')
    try:
        with open(path) as f:
            return json.loads(f.read())
    except (OSError, json.decoder.JSONDecodeError):
        return None


def is_valid_code(code):
    words = code.split('-')
    if len(words) != 3:
        return False
    if not words[0].isdigit():
        return False
    if not words[1] in wordlist:
        return False
    if not words[2] in wordlist:
        return False
    return True


class InviteReceiver(QObject):

    # Wormhole
    got_welcome = Signal(dict)
    #got_code = Signal(str)
    got_introduction = Signal()
    got_message = Signal(dict)
    closed = Signal()

    # SetupRunner
    grid_already_joined = Signal(str)
    update_progress = Signal(str)
    got_icon = Signal(str)
    client_started = Signal(object)
    joined_folders = Signal(list)
    done = Signal(object)

    def __init__(self, known_gateways=None, use_tor=False):
        super(InviteReceiver, self).__init__()
        self.known_gateways = known_gateways
        self.use_tor = use_tor

        self.setup_runner = SetupRunner(known_gateways, use_tor)
        self.setup_runner.grid_already_joined.connect(
            self.grid_already_joined.emit)
        self.setup_runner.update_progress.connect(self.update_progress.emit)
        self.setup_runner.got_icon.connect(self.got_icon.emit)
        self.setup_runner.client_started.connect(self.client_started.emit)
        self.setup_runner.joined_folders.connect(self.joined_folders.emit)
        self.setup_runner.done.connect(self.done.emit)

        self.wormhole = Wormhole(use_tor)
        self.wormhole.got_welcome.connect(self.got_welcome.emit)
        self.wormhole.got_introduction.connect(self.got_introduction.emit)
        self.wormhole.got_message.connect(self.got_message.emit)
        self.wormhole.closed.connect(self.closed.emit)

    def cancel(self):
        self.wormhole.close()

    @inlineCallbacks
    def _run_setup(self, settings, from_wormhole):
        settings = validate_settings(
            settings, self.known_gateways, None, from_wormhole)
        yield self.setup_runner.run(settings)

    @inlineCallbacks
    def receive(self, code, settings=None):
        # TODO: Calculate/emit total steps
        if settings:
            yield self._run_setup(settings, from_wormhole=False)
        elif code.split('-')[0] == '0':
            settings = load_settings_from_cheatcode(code[2:])
            if settings:
                yield self._run_setup(settings, from_wormhole=False)
        else:
            settings = yield self.wormhole.receive(code)
            yield self._run_setup(settings, from_wormhole=True)


class InviteSender(QObject):

    created_invite = Signal()

    # Wormhole
    got_welcome = Signal(dict)
    got_code = Signal(str)
    got_introduction = Signal()
    send_completed = Signal()
    closed = Signal()

    def __init__(self, use_tor=False):
        super(InviteSender, self).__init__()
        self.use_tor = use_tor

        self.wormhole = Wormhole(use_tor)
        self.wormhole.got_welcome.connect(self.got_welcome.emit)
        self.wormhole.got_code.connect(self.got_code.emit)
        self.wormhole.got_introduction.connect(self.got_introduction.emit)
        self.wormhole.send_completed.connect(self.send_completed.emit)
        self.wormhole.closed.connect(self.closed.emit)

        self._pending_invites = []
        self._gateway = None

    def cancel(self):
        self.wormhole.close()
        if self._pending_invites:
            for folder, member_id in self._pending_invites:
                self._gateway.magic_folder_uninvite(folder, member_id)

    @staticmethod
    @inlineCallbacks
    def _get_folder_invite(gateway, folder):
        member_id = b58encode(os.urandom(8))
        code = yield gateway.magic_folder_invite(folder, member_id)
        return folder, member_id, code

    @inlineCallbacks
    def _get_folder_invites(self, gateway, folders):
        folders_data = {}
        tasks = []
        for folder in folders:
            tasks.append(self._get_folder_invite(gateway, folder))
        results = yield DeferredList(tasks, consumeErrors=True)
        for success, result in results:
            if success:
                folder, member_id, code = result
                folders_data[folder] = {'code': code}
                self._pending_invites.append((folder, member_id))
            else:  # Failure
                raise result.type(result.value)
        return folders_data

    @inlineCallbacks
    def send(self, gateway, folders=None):
        settings = gateway.get_settings()
        if folders:
            self._gateway = gateway
            folders_data = yield self._get_folder_invites(gateway, folders)
            settings['magic-folders'] = folders_data
        self.created_invite.emit()
        yield self.wormhole.send(settings)
