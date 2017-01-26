# -*- coding: utf-8 -*-

import logging
import os
import shutil
import sys

from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)
# qt5reactor must be 'installed' after initializing QApplication but
# before running/importing any other Twisted code.
# See https://github.com/gridsync/qt5reactor/blob/master/README.rst
import qt5reactor
qt5reactor.install()
from PyQt5.QtWidgets import QMessageBox  # pylint: disable=all

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.protocol import Protocol, Factory

from gridsync import config_dir, settings
from gridsync.invite import InviteForm
from gridsync.main_window import MainWindow
from gridsync.systray import SystemTrayIcon
from gridsync.tahoe import Tahoe
from gridsync.wizard import Wizard


class CoreProtocol(Protocol):  # pylint: disable=no-init
    def dataReceived(self, data):
        command = data.decode()
        logging.debug("Received command: %s", command)
        if command.lower() in ('stop', 'quit', 'exit'):
            reactor.stop()


class CoreFactory(Factory):
    protocol = CoreProtocol


class Core(object):
    def __init__(self, args):
        self.args = args
        self.tray = None
        self.invite_form = None
        self.main_window = None

    def notify(self, title, message):
        if not self.args.no_gui:
            self.tray.showMessage(title, message, msecs=5000)
        else:
            print(title, message)

    def show_invite_form(self):
        nodedir = os.path.join(config_dir, 'default')
        if os.path.isdir(nodedir):
            reply = QMessageBox.question(
                self.invite_form, "Tahoe-LAFS already configured",
                "Tahoe-LAFS is already configured on this computer. "
                "Do you want to overwrite your existing configuration?")
            if reply == QMessageBox.Yes:
                shutil.rmtree(nodedir, ignore_errors=True)
            else:
                return
        self.invite_form.show()
        self.invite_form.raise_()

    def show_main_window(self):
        self.main_window.show()
        self.main_window.raise_()

    def get_nodedirs(self):
        nodedirs = []
        for filename in os.listdir(config_dir):
            filepath = os.path.join(config_dir, filename)
            confpath = os.path.join(filepath, 'tahoe.cfg')
            if os.path.isdir(filepath) and os.path.isfile(confpath):
                nodedirs.append(filepath)
        logging.debug("Found nodedirs: %s", nodedirs)
        return nodedirs

    def stop_gateways(self):
        logging.debug("Stopping Tahoe-LAFS gateway(s)...")
        for nodedir in self.get_nodedirs():
            gateway = Tahoe(nodedir)
            gateway.stop()

    def stop(self):
        self.stop_gateways()
        logging.debug("Stopping reactor...")

    def start_gateways(self):
        logging.debug("Starting Tahoe-LAFS gateway(s)...")
        for nodedir in self.get_nodedirs():
            gateway = Tahoe(nodedir)
            gateway.start()

    @inlineCallbacks
    def first_run(self):
        defaults = settings['default']
        if defaults['provider_name']:
            nodedir = os.path.join(config_dir, defaults['provider_name'])
            if not os.path.isdir(nodedir):
                tahoe = Tahoe(nodedir)
                yield tahoe.create(**defaults)
                self.start_gateways()
        else:
            wizard = Wizard(self)
            wizard.exec_()
            if not wizard.is_complete:
                logging.debug("Setup wizard not completed; exiting")
                reactor.stop()
            else:
                self.start_gateways()

    def start(self):
        # Listen on a port to prevent multiple instances from running
        reactor.listenTCP(52045, CoreFactory(), interface='localhost')
        try:
            os.makedirs(config_dir)
        except OSError:
            pass
        if self.args.debug:
            logging.basicConfig(
                format='%(asctime)s %(funcName)s %(message)s',
                level=logging.DEBUG, stream=sys.stdout)
        else:
            appname = settings['application']['name']
            logfile = os.path.join(config_dir, '{}.log'.format(appname))
            logging.basicConfig(
                format='%(asctime)s %(funcName)s %(message)s',
                level=logging.INFO, filename=logfile)
        logging.info("Core starting with args: %s", self.args)
        logging.debug("$PATH is: %s", os.getenv('PATH'))
        logging.debug("Loaded config.txt settings: %s", settings)

        if not self.get_nodedirs():
            reactor.callLater(0, self.first_run)
        else:
            reactor.callLater(0, self.start_gateways)

        if not self.args.no_gui:
            self.tray = SystemTrayIcon(self)
            self.tray.show()
            self.invite_form = InviteForm()
            self.main_window = MainWindow(self)

        reactor.addSystemEventTrigger("before", "shutdown", self.stop)
        reactor.run()
