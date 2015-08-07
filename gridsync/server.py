# -*- coding: utf-8 -*-

import logging
import os
import subprocess
import sys

from PyQt4.QtGui import QApplication
app = QApplication(sys.argv)
from qtreactor import pyqt4reactor
pyqt4reactor.install()

from twisted.internet import reactor, task
from twisted.internet.protocol import Protocol, Factory

from gridsync.config import Config
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
        self.sync_state = 0
        self.config = Config(self.args.config)
        self.servers_connected = 0
        self.servers_known = 0
        self.status_text = 'Status: '
        logfile = os.path.join(self.config.config_dir, 'gridsync.log')
        logging.basicConfig(
                format='%(asctime)s %(funcName)s %(message)s',
                stream=sys.stdout,
                #filename=logfile,
                #filemode='w',
                level=logging.DEBUG)

    def build_objects(self):
        logging.info("Building Tahoe objects...")
        logging.info(self.settings)
        for node, settings in self.settings.items():
            t = Tahoe(self, os.path.join(self.config.config_dir, node), settings)
            self.gateways.append(t)

    def handle_command(self, command):
        if command.lower().startswith('gridsync:'):
            logging.info('Got gridsync URI: {}'.format(command))
        elif command.lower() in ('stop', 'quit', 'exit'):
            self.stop()
        else:
            logging.info("Invalid command: {}".format(command))

    def check_state(self):
        if self.sync_state:
            self.tray.start_animation()
        else:
            self.tray.stop_animation()

    def notify(self, title, message):
        self.tray.show_message(title, message)

    def start_gateways(self):
        logging.info("Starting Tahoe-LAFS gateway(s)...")
        logging.info(self.gateways)
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
            tahoe = output.split('\n')[0]
            logging.info("tahoe --version-and-path = {}".format(tahoe))
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
            loop = task.LoopingCall(self.check_state)
            loop.start(1.0)
        reactor.callLater(10, self.update_connection_status) # XXX Fix
        reactor.addSystemEventTrigger("before", "shutdown", self.stop)
        reactor.run()
        sys.exit()

    def update_connection_status(self):
        self.servers_connected = 0
        self.servers_known = 0
        for gateway in self.gateways:
            self.servers_connected += gateway.connection_status['servers_connected']
            self.servers_known += gateway.connection_status['servers_known']
        # XXX Add logic to check for paused state, etc.
        self.status_text = "Status: Connected ({} of {} servers)".format(
                self.servers_connected, self.servers_known)

    def stop(self):
        #self.stop_watchers()
        self.stop_gateways()
        self.config.save(self.settings)
        reactor.stop()
        #sys.exit()

    def stop_gateways(self):
        logging.info("Stopping Tahoe-LAFS gateway(s)...")
        for gateway in self.gateways:
            reactor.callInThread(gateway.stop)

