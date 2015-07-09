# -*- coding: utf-8 -*-

import os
import sys
import time
import threading
import subprocess
import logging

try:
    del sys.modules['twisted.internet.reactor'] # Workaround for PyInstaller
except KeyError:
    pass

from PyQt4.QtGui import QApplication
app = QApplication(sys.argv)
from qtreactor import pyqt4reactor
pyqt4reactor.install()

from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor, task

from config import Config
from tahoe import Tahoe, bin_tahoe
from watcher import Watcher
from systray import SystemTrayIcon


class ServerProtocol(Protocol):
    def dataReceived(self, data):
        logging.debug("Received command: " + str(data))
        self.factory.parent.handle_command(data)


class ServerFactory(Factory):
    protocol = ServerProtocol
    def __init__(self, parent):
        self.parent = parent


class Server():
    def __init__(self, args):
        self.args = args
        self.gateways = []
        self.watchers = []
        self.sync_state = 0

        self.config = Config(self.args.config)

        logfile = os.path.join(self.config.config_dir, 'gridsync.log')
        logging.basicConfig(
                format='%(asctime)s %(message)s', 
                filename=logfile, 
                #filemode='w',
                level=logging.DEBUG)
        logging.info("Server initialized: " + str(args))
        #if sys.platform == 'darwin': # Workaround for PyInstaller
        #    os.environ["PATH"] += os.pathsep + "/usr/local/bin" + os.pathsep \
        #            + "/Applications/tahoe.app/bin" + os.pathsep \
        #            + os.path.expanduser("~/Library/Python/2.7/bin") \
        #            + os.pathsep + os.path.dirname(sys.executable) \
        #            + '/Tahoe-LAFS/bin'
        #logging.debug("$PATH is: " + os.getenv('PATH'))
        logging.info("Found bin/tahoe: " + bin_tahoe())

        try:
            self.settings = self.config.load()
        except IOError:
            self.settings = {}

        self.tray = SystemTrayIcon(self)

        try:
            output = subprocess.check_output(["tahoe", "-V"])
            tahoe = output.split('\n')[0]
            logging.info("tahoe -V = " + tahoe)
        except OSError:
            logging.error('Tahoe-LAFS installation not found; exiting')
            sys.exit()

    def build_objects(self):
        logging.info("Building objects...")
        logging.info(self.settings)
        for node, settings in self.settings.items():
            t = Tahoe(os.path.join(self.config.config_dir, node), settings)
            self.gateways.append(t)
            for local_dir, dircap in self.settings[node]['sync'].items():
                w = Watcher(self, t, os.path.expanduser(local_dir), dircap)
                self.watchers.append(w)

    def handle_command(self, command):
        if command.lower().startswith('gridsync:'):
            logging.info('got gridsync uri')
        elif command == "stop" or command == "quit":
            self.stop()
        else:
            logging.info("Invalid command: " + command)

    def check_state(self):
        if self.sync_state:
            self.tray.start_animation()
        else:
            self.tray.stop_animation()

    def notify(self, title, message):
        self.tray.show_message(title, message)

    def start_gateways(self):
        logging.info("Starting gateway(s)...")
        logging.info(self.gateways)
        threads = [threading.Thread(target=o.start) for o in self.gateways]
        [t.start() for t in threads]
        [t.join() for t in threads]

    def start_watchers(self):
        threads = [threading.Thread(target=o.start) for o in self.watchers]
        [t.start() for t in threads]
        #[t.join() for t in threads]

    def first_run(self):
        from wizard import Wizard
        w = Wizard(self)
        w.exec_()
        logging.debug("Got first run settings: ", self.settings)

        self.build_objects()
        self.start_gateways()
        time.sleep(3)
        self.start_watchers()

    def start(self):
        reactor.listenTCP(52045, ServerFactory(self), interface='localhost')
        self.tray.show()
        loop = task.LoopingCall(self.check_state)
        loop.start(1.0)
        #self.start_gateways()
        #time.sleep(3)
        #self.start_watchers()
        if not self.settings:
            reactor.callLater(0, self.first_run)
        else:
            self.build_objects()
            reactor.callLater(0, self.start_gateways)
            reactor.callLater(3, self.start_watchers)
        reactor.addSystemEventTrigger("before", "shutdown", self.stop)
        reactor.run()
        #sys.exit(app.exec_())

    def stop(self):
        self.stop_watchers()
        #self.stop_gateways()
        self.config.save(self.settings)
    
    def stop_watchers(self):
        threads = [threading.Thread(target=o.stop) for o in self.watchers]
        [t.start() for t in threads]
        [t.join() for t in threads]
        
    def stop_gateways(self):
        threads = [threading.Thread(target=o.stop) for o in self.gateways]
        [t.start() for t in threads]
        [t.join() for t in threads]
        #reactor.stop()

