# -*- coding: utf-8 -*-

import logging
from collections import defaultdict

from PyQt5.QtCore import pyqtSignal, QObject
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall


class Monitor(QObject):

    connected = pyqtSignal(str)
    disconnected = pyqtSignal(str)
    nodes_updated = pyqtSignal(int, int)
    space_updated = pyqtSignal(object)
    data_updated = pyqtSignal(str, object)
    status_updated = pyqtSignal(str, int)
    mtime_updated = pyqtSignal(str, int)
    size_updated = pyqtSignal(str, object)
    member_added = pyqtSignal(str, str)
    first_sync_started = pyqtSignal(str)
    sync_started = pyqtSignal(str)
    sync_finished = pyqtSignal(str)
    files_updated = pyqtSignal(str, list)
    check_finished = pyqtSignal()
    remote_folder_added = pyqtSignal(str, str)

    def __init__(self, gateway):
        super(Monitor, self).__init__()
        self.gateway = gateway
        self.status = defaultdict(dict)
        self.members = []
        self.timer = LoopingCall(self.check_status)
        self.num_connected = 0
        self.num_happy = 0
        self.is_connected = False
        self.available_space = 0

    def add_updated_file(self, folder_name, path):
        if 'updated_files' not in self.status[folder_name]:
            self.status[folder_name]['updated_files'] = []
        if path in self.status[folder_name]['updated_files']:
            return
        elif path.endswith('/') or path.endswith('~') or path.isdigit():
            return
        else:
            self.status[folder_name]['updated_files'].append(path)
            logging.debug("Added %s to updated_files list", path)

    def notify_updated_files(self, folder_name):
        if 'updated_files' in self.status[folder_name]:
            updated_files = self.status[folder_name]['updated_files']
            if updated_files:
                self.status[folder_name]['updated_files'] = []
                logging.debug("Cleared updated_files list")
                self.files_updated.emit(folder_name, updated_files)

    @staticmethod
    def parse_status(status):
        state = 0
        t = 0
        kind = ''
        path = ''
        failures = []
        if status:
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

    def process_magic_folder_status(self, name, status):  # noqa: max-complexit=11
        remote_scan_needed = False
        prev = self.status[name]
        state, kind, filepath, _ = self.parse_status(status)
        if status and prev:
            if state == 1:  # "Syncing"
                if prev['state'] == 0:  # First sync after restoring
                    self.first_sync_started.emit(name)
                if prev['state'] != 1:  # Sync just started
                    logging.debug("Sync started (%s)", name)
                    self.sync_started.emit(name)
                elif prev['state'] == 1:  # Sync started earlier; still going
                    logging.debug("Sync in progress (%s)", name)
                    logging.debug("%sing %s...", kind, filepath)
                    for item in status:
                        if item not in prev['status']:
                            self.add_updated_file(name, item['path'])
            elif state == 2 and prev['state'] == 1:  # Sync just finished
                logging.debug("Sync complete (%s)", name)
                self.sync_finished.emit(name)
                self.notify_updated_files(name)
            if state in (1, 2) and prev['state'] != 2:
                remote_scan_needed = True
            if state != prev['state']:
                self.status_updated.emit(name, state)
        else:
            self.status_updated.emit(name, state)
        self.status[name]['status'] = status
        self.status[name]['state'] = state
        # TODO: Notify failures/conflicts
        return remote_scan_needed

    @inlineCallbacks
    def do_remote_scan(self, name, members=None):
        mems, size, t, _ = yield self.gateway.get_magic_folder_info(
            name, members)
        if mems and len(mems) > 1:
            for member in mems:
                if member not in self.members:
                    self.member_added.emit(name, member[0])
                    self.members.append(member)
        self.size_updated.emit(name, size)
        self.mtime_updated.emit(name, t)

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
                self.remote_folder_added.emit(name, overlay_file)
                c = yield self.gateway.get_json(caps['collective_dircap'])
                members = yield self.gateway.get_magic_folder_members(name, c)
                yield self.do_remote_scan(name, members)

    @inlineCallbacks
    def check_grid_status(self):
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
                    self.connected.emit(self.gateway.name)
                    yield self.scan_rootcap()  # TODO: Move to Monitor?
            elif num_happy and num_connected < num_happy:
                if self.is_connected:
                    self.is_connected = False
                    self.disconnected.emit(self.gateway.name)
            self.num_connected = num_connected
            self.num_happy = num_happy

    @inlineCallbacks
    def check_status(self):
        yield self.check_grid_status()
        for folder in list(self.gateway.magic_folders.keys()):
            status = yield self.gateway.get_magic_folder_status(folder)
            scan_needed = self.process_magic_folder_status(folder, status)
            if scan_needed:
                yield self.do_remote_scan(folder)
        self.check_finished.emit()

    def start(self, interval=2):
        self.timer.start(interval, now=True)
