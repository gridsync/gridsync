# -*- coding: utf-8 -*-

import logging
import os
import sys

from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)
# qt5reactor must be 'installed' after initializing QApplication but
# before running/importing any other Twisted code.
# See https://github.com/gridsync/qt5reactor/blob/master/README.rst
import qt5reactor
qt5reactor.install()

from twisted.internet import reactor
from twisted.internet.defer import DeferredList, gatherResults, inlineCallbacks
from twisted.internet.protocol import Protocol, Factory
from twisted.python.procutils import which

from gridsync import config_dir, pkgdir, settings
from gridsync.gui import Gui
from gridsync.tahoe import get_nodedirs, Tahoe


class CoreProtocol(Protocol):  # pylint: disable=no-init
    def dataReceived(self, data):
        command = data.decode()
        logging.debug("Received command: %s", command)
        if command.lower() in ('stop', 'quit', 'exit'):
            reactor.stop()


class CoreFactory(Factory):  # pylint: disable=no-init
    protocol = CoreProtocol


class Core(object):
    def __init__(self, args):
        self.args = args
        self.gui = None
        self.gateways = []
        self.executable = None
        self.operations = []

    @inlineCallbacks
    def select_executable(self):
        if sys.platform == 'darwin' and getattr(sys, 'frozen', False):
            # Because magic-folder on macOS has not yet landed upstream
            self.executable = os.path.join(pkgdir, 'Tahoe-LAFS', 'tahoe')
            logging.debug("Selected executable: %s", self.executable)
            return
        executables = which('tahoe')
        if executables:
            tasks = []
            for executable in executables:
                logging.debug("Found %s; getting version...", executable)
                tasks.append(Tahoe(executable=executable).version())
            results = yield gatherResults(tasks)
            for executable, version in results:
                logging.debug("%s has version '%s'", executable, version)
                try:
                    major = int(version.split('.')[0])
                    minor = int(version.split('.')[1])
                    if (major, minor) >= (1, 12):
                        self.executable = executable
                        logging.debug("Selected executable: %s", executable)
                        return
                except (IndexError, ValueError):
                    logging.warning(
                        "Could not parse/compare version of '%s'", version)
        if not self.executable:
            logging.critical(
                "Could not find a suitable 'tahoe' executable in your PATH. "
                "Please install Tahoe-LAFS (version >= 1.12) and try again.")
            reactor.stop()

    @inlineCallbacks
    def stop_gateways(self):
        logging.debug("Stopping Tahoe-LAFS gateway(s)...")
        tasks = []
        for nodedir in get_nodedirs(config_dir):
            tasks.append(Tahoe(nodedir, executable=self.executable).stop())
        yield DeferredList(tasks)

    @inlineCallbacks
    def stop(self):
        self.gui.hide()
        yield self.stop_gateways()
        logging.debug("Stopping reactor...")

    @inlineCallbacks
    def start_gateways(self):
        nodedirs = get_nodedirs(config_dir)
        if nodedirs:
            yield self.select_executable()
            logging.debug("Starting Tahoe-LAFS gateway(s)...")
            for nodedir in nodedirs:
                gateway = Tahoe(nodedir, executable=self.executable)
                self.gateways.append(gateway)
                gateway.start()
            self.gui.populate(self.gateways)
        else:
            defaults = settings['default']
            if defaults['provider_name']:
                nodedir = os.path.join(config_dir, defaults['provider_name'])
                yield self.select_executable()
                gateway = Tahoe(nodedir, executable=self.executable)
                self.gateways.append(gateway)
                # TODO: Show setup progress dialog
                yield gateway.create_client(**defaults)
                gateway.start()
                self.gui.populate(self.gateways)
            else:
                self.gui.show_invite_form()
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
        self.gui.systray.show()

        reactor.callLater(0, self.start_gateways)
        reactor.addSystemEventTrigger("before", "shutdown", self.stop)
        reactor.run()
