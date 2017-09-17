# -*- coding: utf-8 -*-

import logging
#import time
from collections import defaultdict
from datetime import datetime

from humanize import naturaltime
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall

from gridsync.preferences import get_preference
from gridsync.util import humanized_list


class Monitor(object):
    def __init__(self, model):
        self.model = model
        self.grid_status = ''
        self.status = defaultdict(dict)
        self.members = []
        self.files = {}
        self.timer = LoopingCall(self.check_status)

    def add_operation(self, item):
        if item not in self.model.gui.core.operations:
            self.model.gui.core.operations.append(item)

    def remove_operation(self, item):
        if item in self.model.gui.core.operations:
            self.model.gui.core.operations.remove(item)

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
            updated_files = self.status[magic_folder]['updated_files']
            if updated_files:
                title = magic_folder.name + " updated and encrypted"
                message = "Updated " + humanized_list(updated_files)
                if get_preference('notifications', 'folder') != 'false':
                    self.model.gui.show_message(title, message)
                self.status[magic_folder]['updated_files'] = []
                logging.debug("Cleared updated_files list")

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
        last_sync = ''
        if state == 1:
            last_sync = "In progress"
        elif t:
            last_sync = naturaltime(datetime.now() - datetime.fromtimestamp(t))
        return state, last_sync, kind, path, failures

    @inlineCallbacks  # noqa: max-complexity=13 XXX
    def check_magic_folder_status(self, magic_folder):
        prev = self.status[magic_folder]
        status = yield magic_folder.get_magic_folder_status()
        state, last_sync, kind, filepath, _ = self.parse_status(status)
        #sync_start_time = 0
        if not prev:
            self.model.set_data(magic_folder.name, magic_folder)
        if status and prev:
            if state == 1:  # "Syncing"
                if prev['state'] == 0:  # First sync after restoring
                    self.model.unfade_row(magic_folder.name)
                    self.model.update_folder_icon(
                        magic_folder.name, magic_folder.magic_folder_path)
                    self.add_operation(magic_folder)
                elif prev['state'] != 1:  # Sync just started
                    logging.debug("Sync started (%s)", magic_folder.name)
                    self.add_operation(magic_folder)
                    #sync_start_time = time.time()
                elif prev['state'] == 1:  # Sync started earlier; still going
                    logging.debug("Sync in progress (%s)", magic_folder.name)
                    logging.debug("%sing %s...", kind, filepath)
                    #sync_start_time = prev['sync_start_time']
                    for item in status:
                        if item not in prev['status']:
                            self.add_updated_file(magic_folder, item['path'])
            elif state == 2 and prev['state'] == 1:  # Sync just finished
                logging.debug("Sync complete (%s)", magic_folder.name)
                self.remove_operation(magic_folder)
                self.notify_updated_files(magic_folder)
                self.model.update_folder_icon(
                    magic_folder.name,
                    magic_folder.magic_folder_path,
                    'lock-closed-green.svg')
            if state in (1, 2) and prev['state'] != 2:
                mems, size, _, _ = yield magic_folder.get_magic_folder_info()
                if len(mems) > 1:
                    for member in mems:
                        if member not in self.members:
                            self.model.add_member(magic_folder.name, member[0])
                            self.members.append(member)
                self.model.set_size(magic_folder.name, size)
        self.status[magic_folder]['status'] = status
        self.status[magic_folder]['state'] = state
        #self.status[magic_folder]['sync_start_time'] = sync_start_time
        self.model.set_status(magic_folder.name, state)
        self.model.set_last_sync(magic_folder.name, last_sync)
        # TODO: Notify failures/conflicts

    @inlineCallbacks
    def scan_rootcap(self, overlay_file=None):
        folders = yield self.model.gateway.get_magic_folders_from_rootcap()
        for name, caps in folders.items():
            if not self.model.findItems(name):
                self.model.add_folder(name, caps, 3)
                self.model.fade_row(name, overlay_file)
                c = yield self.model.gateway.get_json(caps['collective'])
                m = yield self.model.gateway.get_magic_folder_members(c)
                _, s, t, _ = yield self.model.gateway.get_magic_folder_info(m)
                self.model.set_size(name, s)
                mtime = naturaltime(datetime.now() - datetime.fromtimestamp(t))
                self.model.set_last_sync(name, mtime)
                self.model.add_download_button(name)

    @inlineCallbacks
    def check_grid_status(self):
        num_connected = yield self.model.gateway.get_connected_servers()
        if not num_connected:
            grid_status = "Connecting..."
        elif num_connected == 1:
            grid_status = "Connected to {} storage node".format(num_connected)
        else:
            grid_status = "Connected to {} storage nodes".format(num_connected)
        if num_connected and grid_status != self.grid_status:
            if get_preference('notifications', 'connection') != 'false':
                self.model.gui.show_message(
                    self.model.gateway.name, grid_status)
            yield self.scan_rootcap()
        self.grid_status = grid_status

    @inlineCallbacks
    def check_status(self):
        yield self.check_grid_status()
        for magic_folder in self.model.gateway.magic_folders:
            yield self.check_magic_folder_status(magic_folder)

    def start(self, interval=2):
        self.timer.start(interval, now=True)
