# -*- coding: utf-8 -*-

from collections import defaultdict
import logging
import time

from PyQt5.QtCore import pyqtSignal, QObject
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall


class MagicFolderChecker(QObject):

    sync_started = pyqtSignal()
    sync_finished = pyqtSignal()

    transfer_progress_updated = pyqtSignal(object, object)
    transfer_speed_updated = pyqtSignal(object)
    transfer_seconds_remaining_updated = pyqtSignal(object)

    status_updated = pyqtSignal(int)
    mtime_updated = pyqtSignal(int)
    size_updated = pyqtSignal(object)

    members_updated = pyqtSignal(list)

    file_updated = pyqtSignal(object)
    files_updated = pyqtSignal(list, str, str)

    def __init__(self, gateway, name, remote=False):
        super(MagicFolderChecker, self).__init__()
        self.gateway = gateway
        self.name = name
        self.remote = remote

        self.state = None
        self.mtime = 0
        self.size = 0

        self.members = []
        self.history = {}

        self.updated_files = []
        self.initial_scan_completed = False

        self.sync_time_started = 0

    def notify_updated_files(self):
        changes = defaultdict(list)
        for item in self.updated_files:
            changes[item['member']].insert(
                int(item['mtime']), (item['action'], item['path'])
            )
        self.updated_files = []
        for author, change in changes.items():
            notifications = defaultdict(list)
            for action, path in change:
                if path not in notifications[action]:
                    notifications[action].append(path)
            for action, files, in notifications.items():
                logging.debug("%s %s %s", author, action, files)
                # Currently, for non-'admin' members, member/author names are
                # random/non-human-meaningful strings, so omit them for now.
                author = ""  # XXX
                self.files_updated.emit(files, action, author)

    def emit_transfer_signals(self, status):
        # XXX This does not take into account erasure coding overhead
        bytes_transferred = 0
        bytes_total = 0
        for task in status:
            if task['queued_at'] >= self.sync_time_started:
                size = task['size']
                if not size:
                    continue
                if task['status'] in ('queued', 'started', 'success'):
                    bytes_total += size
                if task['status'] in ('started', 'success'):
                    bytes_transferred += size * task['percent_done'] / 100
        if bytes_transferred and bytes_total:
            self.transfer_progress_updated.emit(bytes_transferred, bytes_total)
            duration = time.time() - self.sync_time_started
            speed = bytes_transferred / duration
            self.transfer_speed_updated.emit(speed)
            bytes_remaining = bytes_total - bytes_transferred
            seconds_remaining = bytes_remaining / speed
            self.transfer_seconds_remaining_updated.emit(seconds_remaining)
            logging.debug(
                "%s: %s / %s (%s%%); %s seconds remaining",
                self.name, bytes_transferred, bytes_total,
                int(bytes_transferred / bytes_total * 100), seconds_remaining)

    def parse_status(self, status):
        state = 0
        kind = ''
        path = ''
        failures = []
        if status is not None:
            for task in status:
                if task['status'] in ('queued', 'started'):
                    if not self.sync_time_started:
                        self.sync_time_started = task['queued_at']
                    elif task['queued_at'] < self.sync_time_started:
                        self.sync_time_started = task['queued_at']
                    if not task['path'].endswith('/'):
                        state = 1  # "Syncing"
                        kind = task['kind']
                        path = task['path']
                elif task['status'] == 'failure':
                    failures.append(task)
            if not state:
                state = 2  # "Up to date"
                self.sync_time_started = 0
        return state, kind, path, failures

    def process_status(self, status):
        remote_scan_needed = False
        state, kind, filepath, _ = self.parse_status(status)
        if state == 1:  # "Syncing"
            if self.state != 1:  # Sync just started
                logging.debug("Sync started (%s)", self.name)
                self.sync_started.emit()
            elif self.state == 1:  # Sync started earlier; still going
                logging.debug("Sync in progress (%s)", self.name)
                logging.debug("%sing %s...", kind, filepath)
                # TODO: Emit uploading/downloading signal?
            self.emit_transfer_signals(status)
            remote_scan_needed = True
        elif state == 2:
            if self.state == 1:  # Sync just finished
                logging.debug(
                    "Sync complete (%s); doing final scan...", self.name)
                remote_scan_needed = True
                state = 99
            elif self.state == 99:  # Final scan just finished
                logging.debug("Final scan complete (%s)", self.name)
                self.sync_finished.emit()
                self.notify_updated_files()
        if state != self.state:
            self.status_updated.emit(state)
        self.state = state
        # TODO: Notify failures/conflicts
        return remote_scan_needed

    def compare_states(self, current, previous):
        for mtime, data in current.items():
            if mtime not in previous:
                if data['deleted']:
                    data['action'] = 'deleted'
                else:
                    path = data['path']
                    prev_entry = None
                    for prev_data in previous.values():
                        if prev_data['path'] == path:
                            prev_entry = prev_data
                    if prev_entry:
                        if prev_entry['deleted']:
                            data['action'] = 'restored'
                        else:
                            data['action'] = 'updated'
                    elif path.endswith('/'):
                        data['action'] = 'created'
                    else:
                        data['action'] = 'added'
                self.file_updated.emit(data)
                self.updated_files.append(data)

    @inlineCallbacks
    def do_remote_scan(self, members=None):
        members, size, t, history = yield self.gateway.get_magic_folder_state(
            self.name, members)
        if members:
            members = sorted(members)
            if members != self.members:
                self.members = members
                self.members_updated.emit(members)
            self.size_updated.emit(size)
            self.mtime_updated.emit(t)
            self.compare_states(history, self.history)
            self.history = history
            if not self.initial_scan_completed:
                self.updated_files = []  # Skip notifications
                self.initial_scan_completed = True

    @inlineCallbacks
    def do_check(self):
        status = yield self.gateway.get_magic_folder_status(self.name)
        scan_needed = self.process_status(status)
        if scan_needed or not self.initial_scan_completed:
            yield self.do_remote_scan()


class GridChecker(QObject):

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    nodes_updated = pyqtSignal(int, int)
    space_updated = pyqtSignal(object)

    def __init__(self, gateway):
        super(GridChecker, self).__init__()
        self.gateway = gateway
        self.num_connected = 0
        self.num_known = 0
        self.num_happy = 0
        self.is_connected = False
        self.available_space = 0

    @inlineCallbacks
    def do_check(self):
        results = yield self.gateway.get_grid_status()
        if results:
            num_connected, num_known, available_space = results
        else:
            num_connected = 0
            num_known = 0
            available_space = 0
        if available_space != self.available_space:
            self.available_space = available_space
            self.space_updated.emit(available_space)
        num_happy = self.gateway.shares_happy
        if not num_happy:
            num_happy = 0
        if num_connected != self.num_connected or num_known != self.num_known:
            self.nodes_updated.emit(num_connected, num_known)
            if num_happy and num_connected >= num_happy:
                if not self.is_connected:
                    self.is_connected = True
                    self.connected.emit()
            elif num_happy and num_connected < num_happy:
                if self.is_connected:
                    self.is_connected = False
                    self.disconnected.emit()
            self.num_connected = num_connected
            self.num_known = num_known
            self.num_happy = num_happy


class Monitor(QObject):

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    nodes_updated = pyqtSignal(int, int)
    space_updated = pyqtSignal(object)

    remote_folder_added = pyqtSignal(str, str)

    sync_started = pyqtSignal(str)
    sync_finished = pyqtSignal(str)

    transfer_progress_updated = pyqtSignal(str, object, object)
    transfer_speed_updated = pyqtSignal(str, object)
    transfer_seconds_remaining_updated = pyqtSignal(str, object)

    status_updated = pyqtSignal(str, int)
    mtime_updated = pyqtSignal(str, int)
    size_updated = pyqtSignal(str, object)

    members_updated = pyqtSignal(str, list)

    file_updated = pyqtSignal(str, object)
    files_updated = pyqtSignal(str, list, str, str)

    total_sync_state_updated = pyqtSignal(int)

    check_finished = pyqtSignal()

    def __init__(self, gateway):
        super(Monitor, self).__init__()
        self.gateway = gateway
        self.timer = LoopingCall(self.do_checks)

        self.grid_checker = GridChecker(self.gateway)
        self.grid_checker.connected.connect(self.connected.emit)
        self.grid_checker.connected.connect(self.scan_rootcap)  # XXX
        self.grid_checker.disconnected.connect(self.connected.emit)
        self.grid_checker.nodes_updated.connect(self.nodes_updated.emit)
        self.grid_checker.space_updated.connect(self.space_updated.emit)
        self.magic_folder_checkers = {}
        self.total_sync_state = 0

    def add_magic_folder_checker(self, name, remote=False):
        mfc = MagicFolderChecker(self.gateway, name, remote)

        mfc.sync_started.connect(lambda: self.sync_started.emit(name))
        mfc.sync_finished.connect(lambda: self.sync_finished.emit(name))

        mfc.transfer_progress_updated.connect(
            lambda x, y: self.transfer_progress_updated.emit(name, x, y))
        mfc.transfer_speed_updated.connect(
            lambda x: self.transfer_speed_updated.emit(name, x))
        mfc.transfer_seconds_remaining_updated.connect(
            lambda x: self.transfer_seconds_remaining_updated.emit(name, x))

        mfc.status_updated.connect(lambda x: self.status_updated.emit(name, x))
        mfc.mtime_updated.connect(lambda x: self.mtime_updated.emit(name, x))
        mfc.size_updated.connect(lambda x: self.size_updated.emit(name, x))

        mfc.members_updated.connect(
            lambda x: self.members_updated.emit(name, x))

        mfc.file_updated.connect(lambda x: self.file_updated.emit(name, x))
        mfc.files_updated.connect(
            lambda x, y, z: self.files_updated.emit(name, x, y, z))

        self.magic_folder_checkers[name] = mfc

    @inlineCallbacks
    def scan_rootcap(self, overlay_file=None):
        logging.debug("Scanning %s rootcap...", self.gateway.name)
        yield self.gateway.await_ready()
        folders = yield self.gateway.get_magic_folders_from_rootcap()
        if not folders:
            return
        for name, caps in folders.items():
            if name not in self.gateway.magic_folders.keys():
                logging.debug(
                    "Found new folder '%s' in rootcap; adding...", name)
                self.add_magic_folder_checker(name, remote=True)
                self.remote_folder_added.emit(name, overlay_file)
                c = yield self.gateway.get_json(caps['collective_dircap'])
                members = yield self.gateway.get_magic_folder_members(name, c)
                yield self.magic_folder_checkers[name].do_remote_scan(members)

    @inlineCallbacks
    def do_checks(self):
        yield self.grid_checker.do_check()
        for folder in list(self.gateway.magic_folders.keys()):
            if folder not in self.magic_folder_checkers:
                self.add_magic_folder_checker(folder)
            elif self.magic_folder_checkers[folder].remote:
                self.magic_folder_checkers[folder].remote = False
        states = set()
        for magic_folder_checker in list(self.magic_folder_checkers.values()):
            if not magic_folder_checker.remote:
                yield magic_folder_checker.do_check()
                states.add(magic_folder_checker.state)
        if 1 in states or 99 in states:  # At least one folder is syncing
            state = 1
        elif 2 in states and len(states) == 1:  # All folders are up to date
            state = 2
        else:
            state = 0
        if state != self.total_sync_state:
            self.total_sync_state = state
            self.total_sync_state_updated.emit(state)
        self.check_finished.emit()

    def start(self, interval=2):
        self.timer.start(interval, now=True)
