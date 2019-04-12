# -*- coding: utf-8 -*-

import logging
import os

from PyQt5.QtCore import pyqtSignal, QObject
from twisted.internet.defer import inlineCallbacks


class NewscapChecker(QObject):

    message_received = pyqtSignal(object, str)

    def __init__(self, gateway):
        super().__init__()
        self.gateway = gateway

    @inlineCallbacks
    def _download_messages(self, downloads):
        downloads = sorted(downloads)
        for dest, filecap in downloads:
            try:
                yield self.gateway.download(filecap, dest)
            except Exception as e:  # pylint: disable=broad-except
                logging.warning("Error downloading '%s': %s", dest, str(e))
        newest_message_filepath = downloads[-1][0]
        if os.path.exists(newest_message_filepath):
            with open(newest_message_filepath) as f:
                self.message_received.emit(self.gateway, f.read())

    @inlineCallbacks
    def _check_v1(self):
        content = yield self.gateway.get_json(self.gateway.newscap + '/v1')
        if not content:
            return

        try:
            children = content[1]['children']
        except (IndexError, KeyError) as e:
            logging.warning("%s: '%s'", type(e).__name__, str(e))
            return

        messages_dirpath = os.path.join(
            self.gateway.nodedir, 'private', 'newscap_messages')
        if not os.path.isdir(messages_dirpath):
            os.makedirs(messages_dirpath)

        downloads = []
        for file, data in children.items():
            kind = data[0]
            if kind != 'filenode':
                logging.warning("'%s' is a '%s', not a filenode", file, kind)
                continue
            local_filepath = os.path.join(messages_dirpath, file)
            if not os.path.exists(local_filepath):
                downloads.append((local_filepath, data[1]['ro_uri']))
        if downloads:
            yield self._download_messages(downloads)

    @inlineCallbacks
    def do_check(self):
        if not self.gateway.newscap:
            return
        content = yield self.gateway.get_json(self.gateway.newscap)
        if not content:
            return
        try:
            children = content[1]['children']
        except (IndexError, KeyError) as e:
            logging.warning("%s: '%s'", type(e).__name__, str(e))
            return
        #from gridsync.errors import UpgradeRequiredError
        #if 'v2' in children:
        #    raise UpgradeRequiredError
        v1_data = children.get('v1')
        if v1_data:
            if v1_data[0] == 'dirnode':
                yield self._check_v1()
            else:
                logging.warning("'v1' is not a dirnode")
        else:
            logging.warning("No 'v1' object found in newscap")
