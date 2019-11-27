# -*- coding: utf-8 -*-

import logging
import os
from random import randint
import time
import sys

from atomicwrites import atomic_write
from PyQt5.QtCore import pyqtSignal, QObject
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import deferLater

from gridsync import settings


class NewscapChecker(QObject):

    message_received = pyqtSignal(object, str)
    upgrade_required = pyqtSignal(object)

    def __init__(self, gateway):
        super().__init__()
        self.gateway = gateway
        self._started = False
        self.check_delay_min = 30
        self.check_delay_max = 60 * 60 * 24  # 24 hours
        newscap_settings = settings.get("news:{}".format(self.gateway.name))
        if newscap_settings:
            check_delay_min = newscap_settings.get("check_delay_min")
            if check_delay_min:
                self.check_delay_min = int(check_delay_min)
            check_delay_max = newscap_settings.get("check_delay_max")
            if check_delay_max:
                self.check_delay_max = int(check_delay_max)
        if self.check_delay_max < self.check_delay_min:
            self.check_delay_max = self.check_delay_min
        self._last_checked_path = os.path.join(
            self.gateway.nodedir, "private", "newscap.last_checked"
        )

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
                self.message_received.emit(self.gateway, f.read().strip())

    @inlineCallbacks
    def _check_v1(self):
        content = yield self.gateway.get_json(self.gateway.newscap + "/v1")
        if not content:
            return

        try:
            children = content[1]["children"]
        except (IndexError, KeyError) as e:
            logging.warning("%s: '%s'", type(e).__name__, str(e))
            return

        messages_dirpath = os.path.join(
            self.gateway.nodedir, "private", "newscap_messages"
        )
        if not os.path.isdir(messages_dirpath):
            os.makedirs(messages_dirpath)

        downloads = []
        for file, data in children.items():
            kind = data[0]
            if kind != "filenode":
                logging.warning("'%s' is a '%s', not a filenode", file, kind)
                continue
            if sys.platform == "win32":
                file = file.replace(":", "_")
            local_filepath = os.path.join(messages_dirpath, file)
            if not os.path.exists(local_filepath):
                downloads.append((local_filepath, data[1]["ro_uri"]))
        if downloads:
            yield self._download_messages(downloads)

    @inlineCallbacks
    def _do_check(self):
        self._schedule_delayed_check()
        if not self.gateway.newscap:
            return
        yield self.gateway.await_ready()
        content = yield self.gateway.get_json(self.gateway.newscap)
        if not content:
            return
        try:
            children = content[1]["children"]
        except (IndexError, KeyError) as e:
            logging.warning("%s: '%s'", type(e).__name__, str(e))
            return
        if "v2" in children:
            self.upgrade_required.emit(self.gateway)
        v1_data = children.get("v1")
        if v1_data:
            if v1_data[0] == "dirnode":
                yield self._check_v1()
            else:
                logging.warning("'v1' is not a dirnode")
        else:
            logging.warning("No 'v1' object found in newscap")
        with atomic_write(
            self._last_checked_path, mode="w", overwrite=True
        ) as f:
            f.write(str(int(time.time())))

    def _schedule_delayed_check(self, delay=None):
        if not delay:
            delay = randint(self.check_delay_min, self.check_delay_max)
        deferLater(reactor, delay, self._do_check)
        logging.debug("Scheduled newscap check in %i seconds...", delay)

    def start(self):
        if not self._started:
            self._started = True
            try:
                with open(self._last_checked_path) as f:
                    last_checked = int(f.read())
            except (OSError, ValueError):
                last_checked = 0
            seconds_since_last_check = int(time.time()) - last_checked
            if seconds_since_last_check > self.check_delay_max:
                self._schedule_delayed_check(self.check_delay_min)
            else:
                self._schedule_delayed_check()
