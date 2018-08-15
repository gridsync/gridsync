# -*- coding: utf-8 -*-

import logging
import os
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)
# qt5reactor must be 'installed' after initializing QApplication but
# before running/importing any other Twisted code.
# See https://github.com/gridsync/qt5reactor/blob/master/README.rst
import qt5reactor
qt5reactor.install()

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.protocol import Protocol, Factory

from gridsync import config_dir, resource, settings
from gridsync import msg
from gridsync.gui import Gui
from gridsync.preferences import get_preference
from gridsync.tahoe import get_nodedirs, Tahoe, select_executable
from gridsync.tor import get_tor


app.setWindowIcon(QIcon(resource(settings['application']['tray_icon'])))


class CoreFactory(Factory):  # pylint: disable=no-init
    protocol = Protocol


class Core():
    def __init__(self, args):
        self.args = args
        self.gui = None
        self.gateways = []
        self.executable = None
        self.operations = []

    @inlineCallbacks
    def select_executable(self):
        self.executable = yield select_executable()
        logging.debug("Selected executable: %s", self.executable)
        if not self.executable:
            msg.critical(
                "Tahoe-LAFS not found",
                "Could not find a suitable 'tahoe' executable in your PATH. "
                "Please install Tahoe-LAFS version 1.13.0 or greater and try "
                "again.")
            reactor.stop()

    @inlineCallbacks
    def start_gateways(self):
        nodedirs = get_nodedirs(config_dir)
        if nodedirs:
            minimize_preference = get_preference('startup', 'minimize')
            if not minimize_preference or minimize_preference == 'false':
                self.gui.show_main_window()
            yield self.select_executable()
            tor_available = yield get_tor(reactor)
            logging.debug("Starting Tahoe-LAFS gateway(s)...")
            for nodedir in nodedirs:
                gateway = Tahoe(nodedir, executable=self.executable)
                tcp = gateway.config_get('connections', 'tcp')
                if tcp == 'tor' and not tor_available:
                    msg.error(
                        self.gui.main_window,
                        "Error Connecting To Tor Daemon",
                        'The "{}" connection is configured to use Tor, '
                        'however, no running tor daemon was found.\n\n'
                        'This connection will be disabled until you launch '
                        'Tor again.'.format(gateway.name)
                    )
                self.gateways.append(gateway)
                d = gateway.start()
                d.addCallback(gateway.ensure_folder_links)
            self.gui.populate(self.gateways)
        else:
            self.gui.show_welcome_dialog()
            yield self.select_executable()

    def start(self):
        # Listen on a port to prevent multiple instances from running
        reactor.listenTCP(52045, CoreFactory(), interface='localhost')
        try:
            os.makedirs(config_dir)
        except OSError:
            pass

        logging.info("Core starting with args: %s", self.args)
        logging.debug("$PATH is: %s", os.getenv('PATH'))
        logging.debug("Loaded config.txt settings: %s", settings)

        self.gui = Gui(self)
        self.gui.show_systray()

        reactor.callLater(0, self.start_gateways)
        reactor.run()
        for nodedir in get_nodedirs(config_dir):
            Tahoe(nodedir, executable=self.executable).kill()
