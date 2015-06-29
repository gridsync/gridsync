# -*- coding: utf-8 -*-

import os
import sys
import threading
import subprocess
import logging

from PyQt4.QtGui import QApplication
app = QApplication(sys.argv)

try:
    del sys.modules['twisted.internet.reactor'] # Workaround for PyInstaller
except KeyError:
    pass

from qtreactor import pyqt4reactor
pyqt4reactor.install()

from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor

from config import Config
from tahoe import Tahoe
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

#XXX Change to twisted service?
class Server():
    def __init__(self, args):
        self.args = args
        self.tahoe_objects = []
        self.watcher_objects = []
        self.sync_state = 0

        
        self.config = Config(self.args.config)
        self.settings = self.config.load()
        #self.load_config()
        logfile = os.path.join(self.config.config_dir, 'gridsync.log')
        logging.basicConfig(
                format='%(asctime)s %(message)s', 
                filename=logfile, 
                #filemode='w',
                level=logging.DEBUG)
        logging.info("Server initialized: " + str(args))
        if sys.platform == 'darwin': # Workaround for PyInstaller
            os.environ["PATH"] += os.pathsep + "/usr/local/bin"
        logging.info("PATH is: " + os.getenv('PATH'))
        self.tray = SystemTrayIcon(self)

        try:
            output = subprocess.check_output(["tahoe", "-V"])
            tahoe = output.split('\n')[0]
            logging.info("Found: " + tahoe)
        except OSError:
            logging.error('Tahoe-LAFS installation not found; exiting')
            sys.exit()


        for node_name, node_settings in self.settings['tahoe_nodes'].items():
            t = Tahoe(os.path.join(self.config.config_dir, node_name), node_settings)
            self.tahoe_objects.append(t)
            for sync_name, sync_settings in self.settings['sync_targets'].items():
                if sync_settings[0] == node_name:
                    w = Watcher(self, t, os.path.expanduser(sync_settings[1]), sync_settings[2])
                    self.watcher_objects.append(w)

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
        t = threading.Timer(1.0, self.check_state)
        t.setDaemon(True)
        t.start()


    def notify(self, title, message):
        self.gui.show_message('Sync complete', 'blah')

    def start(self):
        reactor.listenTCP(52045, ServerFactory(self), interface='localhost')

        #self.gui.show()
        self.tray.show()

        self.check_state()

        #XXX Defer this
        threads = [threading.Thread(target=o.start) for o in self.tahoe_objects]
        [t.start() for t in threads]
        [t.join() for t in threads]
        #time.sleep(1)

        threads = [threading.Thread(target=o.start) for o in self.watcher_objects]
        [t.start() for t in threads]
        #[t.join() for t in threads]

        reactor.run()
        #sys.exit(app.exec_())

    def stop(self):
        threads = [threading.Thread(target=o.stop) for o in self.watcher_objects]
        [t.start() for t in threads]
        [t.join() for t in threads]
        
        threads = [threading.Thread(target=o.stop) for o in self.tahoe_objects]
        [t.start() for t in threads]
        [t.join() for t in threads]

        self.config.save(self.settings)

        reactor.stop()

