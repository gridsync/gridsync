# -*- coding: utf-8 -*-

import logging

from PyQt5.QtCore import pyqtSignal, QObject
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall


class MagicFolderChecker(QObject):

    first_sync_started = pyqtSignal()
    sync_started = pyqtSignal()
    sync_finished = pyqtSignal()

    status_updated = pyqtSignal(int)
    mtime_updated = pyqtSignal(int)
    size_updated = pyqtSignal(object)

    member_added = pyqtSignal(str)
    member_removed = pyqtSignal(str)

    directory_created = pyqtSignal(object)
    file_added = pyqtSignal(object)
    file_updated = pyqtSignal(object)
    file_deleted = pyqtSignal(object)
    file_restored = pyqtSignal(object)

    directories_created = pyqtSignal(list)
    files_added = pyqtSignal(list)
    files_updated = pyqtSignal(list)
    files_deleted = pyqtSignal(list)
    files_restored = pyqtSignal(list)

    def __init__(self, gateway, name, remote=False):
        super(MagicFolderChecker, self).__init__()
        self.gateway = gateway
        self.name = name
        self.remote = remote

        self.state = None
        self.status = {}
        self.mtime = 0
        self.size = 0

        self.members = []
        self.history = {}

        self.created_directories = []
        self.added_files = []
        self.updated_files = []
        self.deleted_files = []
        self.restored_files = []

        #self.file_added.connect(print)
        #self.file_updated.connect(print)
        #self.file_deleted.connect(print)
        #self.file_restored.connect(print)

    def add_updated_file(self, path):
        if path in self.updated_files or path.endswith('/') \
                or path.endswith('~') or path.isdigit():
            return
        self.updated_files.append(path)
        logging.debug("Added %s to updated_files list", path)

    def notify_updated_files(self):
        updated_files = self.updated_files
        if updated_files:
            self.updated_files = []
            logging.debug("Cleared updated_files list")
            self.files_updated.emit(updated_files)

    # TODO: Handle added/deleted/restored
    # TODO: Batch by author?

    @staticmethod
    def parse_status(status):
        state = 0
        t = 0
        kind = ''
        path = ''
        failures = []
        if status is not None:
            for task in status:
                if 'success_at' in task and task['success_at'] > t:
                    t = task['success_at']
                if task['status'] == 'queued' or task['status'] == 'started':
                    if not task['path'].endswith('/'):
                        state = 1  # "Syncing"
                        kind = task['kind']
                        path = task['path']
                elif task['status'] == 'failure':
                    failures.append(task['path'])
            if not state:
                state = 2  # "Up to date"
        return state, kind, path, failures

    def process_status(self, status):  # noqa: max-complexit=11
        remote_scan_needed = False
        state, kind, filepath, _ = self.parse_status(status)
        if status and self.state:
            if state == 1:  # "Syncing"
                if self.state == 0:  # First sync after restoring
                    self.first_sync_started.emit()
                if self.state != 1:  # Sync just started
                    logging.debug("Sync started (%s)", self.name)
                    self.sync_started.emit()
                elif self.state == 1:  # Sync started earlier; still going
                    logging.debug("Sync in progress (%s)", self.name)
                    logging.debug("%sing %s...", kind, filepath)
                    for item in status:
                        if item not in self.status:
                            self.add_updated_file(item['path'])
            elif state == 2 and self.state == 1:  # Sync just finished
                logging.debug("Sync complete (%s)", self.name)
                self.sync_finished.emit()
                self.notify_updated_files()
            if state in (1, 2) and self.state != 2:
                remote_scan_needed = True
            if state != self.state:
                self.status_updated.emit(state)
        else:
            self.status_updated.emit(state)
        self.status = status
        self.state = state
        # TODO: Notify failures/conflicts
        return remote_scan_needed

    def compare_states(self, current, previous):
        for mtime, data in current.items():
            if mtime not in previous:
                if data['deleted']:
                    self.file_deleted.emit(data)
                else:
                    path = data['path']
                    prev_entry = None
                    for prev_data in previous.values():
                        if prev_data['path'] == path:
                            prev_entry = prev_data
                    if prev_entry:
                        if prev_entry['deleted']:
                            self.file_restored.emit(data)
                        else:
                            self.file_updated.emit(data)
                    elif path.endswith('/'):
                        self.directory_created.emit(data)
                    else:
                        self.file_added.emit(data)

    @inlineCallbacks
    def do_remote_scan(self, members=None):
        members, size, t, history = yield self.gateway.get_magic_folder_state(
            self.name, members)
        if members:
            for member in members:
                if member not in self.members:
                    self.member_added.emit(member[0])
                    self.members.append(member)
        self.size_updated.emit(size)
        self.mtime_updated.emit(t)
        self.compare_states(history, self.history)
        self.history = history

    @inlineCallbacks
    def do_check(self):
        status = yield self.gateway.get_magic_folder_status(self.name)
        scan_needed = self.process_status(status)
        if scan_needed:
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
        self.num_happy = 0
        self.is_connected = False
        self.available_space = 0

    @inlineCallbacks
    def do_check(self):
        results = yield self.gateway.get_grid_status()
        if results:
            num_connected, _, available_space = results
        else:
            num_connected = 0
            available_space = 0
        if available_space != self.available_space:
            self.available_space = available_space
            self.space_updated.emit(available_space)
        num_happy = self.gateway.shares_happy
        if not num_happy:
            num_happy = 0
        if num_connected != self.num_connected or num_happy != self.num_happy:
            self.nodes_updated.emit(num_connected, num_happy)
            if num_happy and num_connected >= num_happy:
                if not self.is_connected:
                    self.is_connected = True
                    self.connected.emit()
            elif num_happy and num_connected < num_happy:
                if self.is_connected:
                    self.is_connected = False
                    self.disconnected.emit()
            self.num_connected = num_connected
            self.num_happy = num_happy


class Monitor(QObject):

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    nodes_updated = pyqtSignal(int, int)
    space_updated = pyqtSignal(object)

    remote_folder_added = pyqtSignal(str, str)

    first_sync_started = pyqtSignal(str)
    sync_started = pyqtSignal(str)
    sync_finished = pyqtSignal(str)

    status_updated = pyqtSignal(str, int)
    mtime_updated = pyqtSignal(str, int)
    size_updated = pyqtSignal(str, object)

    member_added = pyqtSignal(str, str)
    member_removed = pyqtSignal(str, str)

    directory_created = pyqtSignal(str, object)
    file_added = pyqtSignal(str, object)
    file_updated = pyqtSignal(str, object)
    file_deleted = pyqtSignal(str, object)
    file_restored = pyqtSignal(str, object)

    files_updated = pyqtSignal(str, list)

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

    def add_magic_folder_checker(self, name, remote=False):
        mfc = MagicFolderChecker(self.gateway, name, remote)

        mfc.first_sync_started.connect(
            lambda: self.first_sync_started.emit(name))
        mfc.sync_started.connect(lambda: self.sync_started.emit(name))
        mfc.sync_finished.connect(lambda: self.sync_finished.emit(name))

        mfc.status_updated.connect(lambda x: self.status_updated.emit(name, x))
        mfc.mtime_updated.connect(lambda x: self.mtime_updated.emit(name, x))
        mfc.size_updated.connect(lambda x: self.size_updated.emit(name, x))

        mfc.member_added.connect(lambda x: self.member_added.emit(name, x))
        mfc.member_removed.connect(lambda x: self.member_removed.emit(name, x))

        mfc.directory_created.connect(
            lambda x: self.directory_created.emit(name, x))
        mfc.file_added.connect(lambda x: self.file_added.emit(name, x))
        mfc.file_updated.connect(lambda x: self.file_updated.emit(name, x))
        mfc.file_deleted.connect(lambda x: self.file_deleted.emit(name, x))
        mfc.file_restored.connect(lambda x: self.file_restored.emit(name, x))

        mfc.files_updated.connect(lambda x: self.files_updated.emit(name, x))
        # XXX

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
            # TODO: Handle newly-restored folders; set remote=False
        for magic_folder_checker in self.magic_folder_checkers.values():
            if not magic_folder_checker.remote:
                yield magic_folder_checker.do_check()
        self.check_finished.emit()

    def start(self, interval=2):
        self.timer.start(interval, now=True)
