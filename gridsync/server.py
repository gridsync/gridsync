# -*- coding: utf-8 -*-

import logging
import os
import subprocess
import sys

from PyQt4.QtGui import QApplication
app = QApplication(sys.argv)
from qtreactor import pyqt4reactor
pyqt4reactor.install()

from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet.protocol import Protocol, Factory

from gridsync.config import Config
from gridsync.sync import SyncFolder
from gridsync.systray import SystemTrayIcon
from gridsync.tahoe import Tahoe


class ServerProtocol(Protocol):
    def dataReceived(self, data):
        logging.debug("Received command: {}".format(data))
        self.factory.parent.handle_command(data)


class ServerFactory(Factory):
    protocol = ServerProtocol
    def __init__(self, parent):
        self.parent = parent


class Server():
    def __init__(self, args):
        self.args = args
        self.gateways = []
        self.sync_folders = []
        self.config = Config(self.args.config)
        self.servers_connected = 0
        self.servers_known = 0
        self.status_text = 'Status: '
        self.new_messages = []
        if self.args.debug:
            logging.basicConfig(
                    format='%(asctime)s %(funcName)s %(message)s',
                    level=logging.DEBUG,
                    stream=sys.stdout)
        else:
            logfile = os.path.join(self.config.config_dir, 'gridsync.log')
            logging.basicConfig(
                    format='%(asctime)s %(funcName)s %(message)s',
                    level=logging.INFO,
                    filename=logfile)

    def build_objects(self):
        logging.debug("Building Tahoe objects...")
        logging.debug(self.settings)
        for node, settings in self.settings.iteritems():
            t = Tahoe(os.path.join(self.config.config_dir, node), settings)
            self.gateways.append(t)
            for section, settings in settings.iteritems():
                if section == 'sync':
                    for local_dir, dircap in settings.iteritems():
                        self.add_sync_folder(local_dir, dircap, t)

    def add_sync_folder(self, local_dir, dircap=None, tahoe=None):
        logging.debug("Adding SyncFolder ({})...".format(local_dir))
        # TODO: Add error handling
        if not os.path.isdir(local_dir):
            logging.debug("Directory {} doesn't exist; "
                    "creating {}...".format(local_dir, local_dir))
            os.makedirs(local_dir)
        if not dircap:
            logging.debug("No dircap associated with {}; "
                    "creating new dircap...".format(local_dir))
            dircap = tahoe.command(['mkdir'])
            self.settings[tahoe.name]['sync'][local_dir] = dircap
            self.config.save(self.settings)
        sync_folder = SyncFolder(local_dir, dircap, tahoe)
        self.sync_folders.append(sync_folder)

    def start_sync_folders(self):
        logging.debug("Starting SyncFolders...")
        for sync_folder in self.sync_folders:
            reactor.callInThread(sync_folder.start)

    def stop_sync_folders(self):
        logging.debug("Stopping SyncFolders...")
        for sync_folder in self.sync_folders:
            reactor.callInThread(sync_folder.stop)

    def handle_command(self, command):
        if command.lower().startswith('gridsync:'):
            logging.info('Got gridsync URI: {}'.format(command))
            # TODO: Handle this
        elif command.lower() in ('stop', 'quit', 'exit'):
            reactor.stop()
        else:
            logging.info("Invalid command: {}".format(command))

    def check_state(self):
        active_jobs = []
        for sync_folder in self.sync_folders:
            if sync_folder.sync_state:
                active_jobs.append(sync_folder)
                for message in sync_folder.sync_log:
                    self.new_messages.append(message)
                    sync_folder.sync_log.remove(message)
        if active_jobs:
            self.tray.start_animation()
        else:
            self.tray.stop_animation()
            if self.new_messages:
                message = '\n'.join(self.new_messages)
                self.notify("Sync complete", message)
                self.new_messages = []

    def notify(self, title, message):
        self.tray.showMessage(title, message)

    def start_gateways(self):
        logging.debug("Starting Tahoe-LAFS gateway(s)...")
        for gateway in self.gateways:
            reactor.callInThread(gateway.start)

    def first_run(self):
        from tutorial import Tutorial
        t = Tutorial(self)
        t.exec_()
        logging.debug("Got first run settings: ", self.settings)
        self.build_objects()
        self.start_gateways()

    def start(self):
        reactor.listenTCP(52045, ServerFactory(self), interface='localhost')
        logging.info("Server started with args: {}".format((self.args)))
        logging.debug("$PATH is: {}".format(os.getenv('PATH')))
        logging.debug("$PYTHONPATH is: {}".format(os.getenv('PYTHONPATH')))

        try:
            output = subprocess.check_output(["tahoe", "--version-and-path"])
            logging.info(output.split('\n')[0])
        except Exception as e:
            logging.error('Error checking Tahoe-LAFS version: {}'.format(str(e)))

        try:
            self.settings = self.config.load()
        except IOError:
            self.settings = {}

        if not self.settings:
            reactor.callLater(0, self.first_run)
        else:
            self.build_objects()
            reactor.callLater(0, self.start_gateways)
        if not self.args.no_gui:
            self.tray = SystemTrayIcon(self)
            self.tray.show()
            state_checker = LoopingCall(self.check_state)
            state_checker.start(1.0)
        connection_status_updater = LoopingCall(
                reactor.callInThread, self.update_connection_status)
        reactor.callLater(5, connection_status_updater.start, 60)
        reactor.callLater(1, self.start_sync_folders)
        reactor.addSystemEventTrigger("before", "shutdown", self.stop)
        reactor.suggestThreadPoolSize(20) # XXX Adjust?
        reactor.run()

    def update_connection_status(self):
        servers_connected = 0
        servers_known = 0
        for gateway in self.gateways:
            servers_connected += gateway.status['servers_connected']
            servers_known += gateway.status['servers_known']
        self.servers_connected = servers_connected
        self.servers_known = servers_known
        # XXX Add logic to check for paused state, etc.
        self.status_text = "Status: Connected ({} of {} servers)".format(
                self.servers_connected, self.servers_known)

    def stop(self):
        self.stop_sync_folders()
        self.stop_gateways()
        self.config.save(self.settings)
        logging.debug("Stopping reactor...")

    def stop_gateways(self):
        logging.debug("Stopping Tahoe-LAFS gateway(s)...")
        for gateway in self.gateways:
            reactor.callInThread(gateway.command, ['stop'])

