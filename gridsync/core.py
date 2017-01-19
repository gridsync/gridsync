# -*- coding: utf-8 -*-

import logging
import os
import shutil
import sys

from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)
import qt5reactor
qt5reactor.install()
from PyQt5.QtWidgets import QMessageBox  # pylint: disable=all

from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet.protocol import Protocol, Factory

from gridsync import config_dir, settings
from gridsync.config import YamlConfig
from gridsync.deprecated import SyncFolder, Tahoe, DEFAULT_SETTINGS
from gridsync.invite import InviteForm
from gridsync.systray import SystemTrayIcon
from gridsync.util import h2b, b2h
from gridsync.main_window import MainWindow


class CoreProtocol(Protocol):  # pylint: disable=no-init
    def dataReceived(self, data):
        data = data.decode()
        logging.debug("Received command: %s", data)
        if data.lower().startswith('gridsync:'):
            logging.info("Got gridsync URI: %s", data)
            # TODO: Handle this
        elif data.lower() in ('stop', 'quit', 'exit'):
            reactor.stop()
        else:
            logging.info("Invalid command: %s", data)


class CoreFactory(Factory):
    protocol = CoreProtocol

    def __init__(self, parent):
        self.parent = parent


class Core(object):
    def __init__(self, args):
        self.args = args
        self.gateways = []
        self.sync_folders = []
        self.servers_connected = 0
        self.servers_known = 0
        self.total_available_space = 0
        self.status_text = 'Status: '
        self.new_messages = []
        self.settings = {}
        self.tray = None
        self.invite_form = None
        self.main_window = None
        if args.config:
            self.config = YamlConfig(args.config[0])
        else:
            self.config = YamlConfig(os.path.join(config_dir, 'config.yml'))

    def initialize_gateways(self):
        logging.debug("Initializing Tahoe-LAFS gateway(s)...")
        logging.debug(self.settings)
        for gateway in self.settings:
            try:
                t = Tahoe(gateway, self.settings[gateway]['tahoe.cfg'])
            except KeyError:
                t = Tahoe(gateway)
            self.gateways.append(t)
            for section, contents in self.settings[gateway].items():
                if section == 'sync':
                    for local_dir, dircap in contents.items():
                        self.add_sync_folder(local_dir, dircap, t)

    def add_sync_folder(self, local_dir, dircap=None, tahoe=None):
        logging.debug("Adding SyncFolder (%s)...", local_dir)
        # TODO: Add error handling
        if not os.path.isdir(local_dir):
            logging.debug(
                "Directory %s doesn't exist; creating %s...",
                local_dir,
                local_dir)
            os.makedirs(local_dir)
        sync_folder = SyncFolder(self, local_dir, dircap, tahoe)
        self.sync_folders.append(sync_folder)

    def insert_new_dircap(self, sync_folder):
        # FIXME: Ugly hack. This should all probably move to SyncFolder:start
        local_dir = sync_folder.local_dir
        logging.debug(
            "No dircap assaciated with %s; creating new dircap...",
            local_dir)
        dircap = sync_folder.tahoe.command(['mkdir'], num_attempts=10)
        for gateway, node_settings in self.settings.items():
            for setting, value in node_settings.items():
                if setting == 'sync' and value[local_dir] is None:
                    sync_folder.remote_dircap = dircap
                    self.settings[gateway]['sync'][local_dir] = dircap
                    self.config.save(self.settings)
                    if gateway.startswith('pb://'):
                        introducer_furl = gateway
                    else:
                        client_settings = setting['tahoe.cfg']['client']
                        introducer_furl = client_settings['introducer.furl']
                    dircap_txt = os.path.join(
                        local_dir, 'Gridsync Invite Code.txt')
                    with open(dircap_txt, 'w') as f:
                        f.write(
                            'gridsync' + introducer_furl[2:] + '/' + dircap)
                    self.notify("Sync Folder Initialized",
                                "Monitoring {}".format(local_dir))
        reactor.callInThread(sync_folder.start)

    def start_sync_folders(self):
        logging.debug("Starting SyncFolders...")
        for sync_folder in self.sync_folders:
            if not sync_folder.remote_dircap:
                #reactor.callInThread(
                #    reactor.callLater, 5, self.insert_new_dircap, sync_folder)
                reactor.callLater(5, self.insert_new_dircap, sync_folder)
            else:
                reactor.callInThread(sync_folder.start)

    def stop_sync_folders(self):
        logging.debug("Stopping SyncFolders...")
        for sync_folder in self.sync_folders:
            reactor.callInThread(sync_folder.stop)

    def check_state(self):
        active_jobs = []
        for sync_folder in self.sync_folders:
            if sync_folder.sync_state:
                active_jobs.append(sync_folder)
                for message in sync_folder.sync_log:
                    self.new_messages.append(message)
                    sync_folder.sync_log.remove(message)
        if active_jobs:
            if not self.args.no_gui and self.tray.animation.state() != 2:
                self.tray.animation.setPaused(False)
                self.tray.setToolTip("Gridsync - Syncing...")
            for sync_folder in self.sync_folders:
                for operation in sync_folder.tahoe.get_operations():
                    logging.debug(operation)
        else:
            if not self.args.no_gui and self.tray.animation.state() == 2:
                self.tray.animation.setPaused(True)
                self.tray.setToolTip("Gridsync - Up to date")
                self.tray.set_icon(settings['application']['tray_icon'])
            if self.new_messages:
                message = '\n'.join(self.new_messages)
                self.notify("Sync complete", message)
                self.new_messages = []

    def notify(self, title, message):
        if not self.args.no_gui:
            self.tray.showMessage(title, message, msecs=5000)
        else:
            print(title, message)

    def start_gateways(self):
        logging.debug("Starting Tahoe-LAFS gateway(s)...")
        for gateway in self.gateways:
            reactor.callInThread(gateway.start)

    def first_run(self):
        from gridsync.wizard import Wizard
        w = Wizard()
        w.exec_()
        if not w.introducer_furl or not w.folder:
            logging.debug("Setup wizard not completed; exiting")
            reactor.stop()
            return
        self.settings = {w.introducer_furl: {'tahoe.cfg': DEFAULT_SETTINGS}}
        self.settings[w.introducer_furl]['sync'] = {w.folder: None}
        logging.debug("Setup wizard finished. Using: %s", self.settings)
        self.initialize_gateways()
        self.start_gateways()

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

    def start(self):
        reactor.listenTCP(52045, CoreFactory(self), interface='localhost')
        try:
            os.makedirs(config_dir)
        except OSError:
            pass
        if self.args.debug:
            logging.basicConfig(
                format='%(asctime)s %(funcName)s %(message)s',
                level=logging.DEBUG,
                stream=sys.stdout)
        else:
            logfile = os.path.join(config_dir, 'gridsync.log')
            logging.basicConfig(
                format='%(asctime)s %(funcName)s %(message)s',
                level=logging.INFO,
                filename=logfile)
        logging.info("Core started with args: %s", self.args)
        logging.debug("$PATH is: %s", os.getenv('PATH'))
        try:
            self.settings = self.config.load()
        except IOError:
            self.settings = {}
        if not self.settings:
            reactor.callLater(0, self.first_run)
        else:
            self.initialize_gateways()
            reactor.callLater(0, self.start_gateways)
        if not self.args.no_gui:
            self.tray = SystemTrayIcon(self)
            self.tray.show()
            self.invite_form = InviteForm()
            self.main_window = MainWindow(self)
        state_checker = LoopingCall(self.check_state)
        state_checker.start(1.0)
        connection_status_updater = LoopingCall(
            reactor.callInThread, self.update_connection_status)
        reactor.callLater(5, connection_status_updater.start, 60)
        reactor.callLater(1, self.start_sync_folders)
        reactor.addSystemEventTrigger("before", "shutdown", self.stop)
        reactor.suggestThreadPoolSize(20)  # XXX Adjust?
        reactor.run()

    def update_connection_status(self):
        servers_connected = 0
        servers_known = 0
        available_space = 0
        for gateway in self.gateways:
            try:
                prev_servers = gateway.status['servers_connected']
            except KeyError:
                pass
            try:
                gateway.update_status()
                servers_connected += gateway.status['servers_connected']
                servers_known += gateway.status['servers_known']
                available_space += h2b(gateway.status['total_available_space'])
            except (OSError, IndexError):
                # XXX
                pass
            try:
                if prev_servers != gateway.status['servers_connected']:
                    # TODO: Notify on (dis)connects
                    # FIXME: This should only be called if a Tahoe flag is set
                    logging.debug("New storage node (dis)connected.")
                    #reactor.callInThread(gateway.adjust)
            except UnboundLocalError:
                pass
        self.servers_connected = servers_connected
        self.total_available_space = b2h(available_space)
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
