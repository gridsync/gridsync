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
from twisted.internet.defer import DeferredList, inlineCallbacks
from twisted.internet.protocol import Protocol, Factory

from gridsync import config_dir, settings
from gridsync.gui import Gui
from gridsync.tahoe import Tahoe


def get_nodedirs():
    nodedirs = []
    for filename in os.listdir(config_dir):
        filepath = os.path.join(config_dir, filename)
        confpath = os.path.join(filepath, 'tahoe.cfg')
        if os.path.isdir(filepath) and os.path.isfile(confpath):
            nodedirs.append(filepath)
    return nodedirs


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

    def notify(self, title, message):
        if self.gui:
            self.gui.show_message(title, message)
        else:
            print(title, message)

    @inlineCallbacks
    def stop_gateways(self):  # pylint: disable=no-self-use
        logging.debug("Stopping Tahoe-LAFS gateway(s)...")
        tasks = []
        for nodedir in get_nodedirs():
            tasks.append(Tahoe(nodedir).stop())
        yield DeferredList(tasks)

    @inlineCallbacks
    def stop(self):
        yield self.stop_gateways()
        logging.debug("Stopping reactor...")

    def start_gateways(self):  # pylint: disable=no-self-use
        logging.debug("Starting Tahoe-LAFS gateway(s)...")
        for nodedir in get_nodedirs():
            Tahoe(nodedir).start()

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
            self.gui.exec_wizard()
            if not self.gui.wizard.is_complete:
                logging.debug("Setup wizard not completed; exiting")
                reactor.stop()
            else:
                self.gui.show()

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

        nodedirs = get_nodedirs()
        for nodedir in nodedirs:
            logging.debug("Found nodedir: %s", nodedir)

        if not nodedirs:
            reactor.callLater(0, self.first_run)
        else:
            reactor.callLater(0, self.start_gateways)

        if not self.args.no_gui:
            self.gui = Gui(self)
            self.gui.systray.show()

        reactor.addSystemEventTrigger("before", "shutdown", self.stop)
        reactor.run()
