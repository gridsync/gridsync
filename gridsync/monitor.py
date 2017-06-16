# -*- coding: utf-8 -*-

import logging
from collections import defaultdict
from datetime import datetime

from humanize import naturaltime
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

from gridsync.util import humanized_list


class Monitor(object):
    def __init__(self, model):
        self.model = model
        self.gateway = self.model.gateway
        self.gui = self.model.gui
        self.grid_status = ''
        self.status = defaultdict(dict)
        self.timer = LoopingCall(self.check_status)

    def add_updated_file(self, magic_folder, path):
        if 'updated_files' not in self.status[magic_folder]:
            self.status[magic_folder]['updated_files'] = []
        if path in self.status[magic_folder]['updated_files']:
            return
        elif path.endswith('/') or path.endswith('~') or path.isdigit():
            return
        else:
            self.status[magic_folder]['updated_files'].append(path)
            logging.debug("Added %s to updated_files list", path)

    def notify_updated_files(self, magic_folder):
        if 'updated_files' in self.status[magic_folder]:
            title = magic_folder.name + " updated and encrypted"
            message = "Updated " + humanized_list(
                self.status[magic_folder]['updated_files'])
            self.gui.show_message(title, message)
            self.status[magic_folder]['updated_files'] = []
            logging.debug("Cleared updated_files list")

    def parse_status(self, status):  # pylint: disable=no-self-use
        state = 0
        t = 0
        if status:
            for task in status:
                if 'success_at' in task and task['success_at'] > t:
                    t = task['success_at']
                if task['status'] == 'queued' or task['status'] == 'started':
                    if not task['path'].endswith('/'):
                        state = 1  # "Syncing"
            if not state:
                state = 2  # "Up to date"
        last_sync = ''
        if t:
            last_sync = naturaltime(datetime.now() - datetime.fromtimestamp(t))
        return state, last_sync

    @inlineCallbacks
    def check_magic_folder_status(self, magic_folder):
        status = yield magic_folder.get_magic_folder_status()
        state, last_sync = self.parse_status(status)
        prev = self.status[magic_folder]
        if status and prev:
            if prev['status'] and status != prev['status']:
                for item in status:
                    if item not in prev['status']:
                        self.add_updated_file(magic_folder, item['path'])
                size = yield magic_folder.get_magic_folder_size()
                self.model.set_size(magic_folder.name, size)
            if state == 2 and prev['state'] != 2:
                self.notify_updated_files(magic_folder)
                size = yield magic_folder.get_magic_folder_size()
                self.model.set_size(magic_folder.name, size)
                if magic_folder in self.gui.core.operations:
                    self.gui.core.operations.remove(magic_folder)
            elif state == 1:
                if magic_folder not in self.gui.core.operations:
                    self.gui.core.operations.append(magic_folder)
        self.status[magic_folder]['status'] = status
        self.status[magic_folder]['state'] = state
        self.model.set_status(magic_folder.name, state)
        self.model.set_last_sync(magic_folder.name, last_sync)

    @inlineCallbacks
    def check_grid_status(self):
        num_connected = yield self.gateway.get_connected_servers()
        if not num_connected:
            grid_status = "Connecting..."
        elif num_connected == 1:
            grid_status = "Connected to {} storage node".format(num_connected)
        else:
            grid_status = "Connected to {} storage nodes".format(num_connected)
        if num_connected and grid_status != self.grid_status:
            self.gui.show_message(self.gateway.name, grid_status)
        self.grid_status = grid_status

    def check_status(self):
        self.check_grid_status()
        for magic_folder in self.gateway.magic_folders:
            self.check_magic_folder_status(magic_folder)

    def start(self, interval=2):
        self.timer.start(interval, now=True)
