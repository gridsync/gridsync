import os
import sys
import threading

from PyQt4.QtGui import QApplication
app = QApplication(sys.argv)

del sys.modules['twisted.internet.reactor'] # Workaround for PyInstaller
from qtreactor import pyqt4reactor
pyqt4reactor.install()

from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor

from gui import Gui
from config import Config
from tahoe import Tahoe
from watcher import Watcher

class ServerProtocol(Protocol):
    def dataReceived(self, data):
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
        self.gui = Gui(self)
        print "Server initialized: " +str(args)
        
        self.config = Config(self.args.config)
        self.settings = self.config.load()
        print "Config loaded: " +self.config.config_file
        #self.load_config()
        for node_name, node_settings in self.settings['tahoe_nodes'].items():
            t = Tahoe(os.path.join(self.config.config_dir, node_name), node_settings)
            self.tahoe_objects.append(t)
            for sync_name, sync_settings in self.settings['sync_targets'].items():
                if sync_settings[0] == node_name:
                    w = Watcher(self, t, os.path.expanduser(sync_settings[1]), sync_settings[2])
                    self.watcher_objects.append(w)

    def handle_command(self, command):
        if command.lower().startswith('gridsync:'):
            print('got gridsync uri')
        elif command == "stop" or command == "quit":
            self.stop()
        else:
            print("Invalid command")


    def check_state(self):
        #print "SYNC STATE IS: " + str(self.sync_state)
        if self.sync_state:
            self.gui.start_animation()
        else:
            self.gui.stop_animation()
        t = threading.Timer(1.0, self.check_state)
        t.setDaemon(True)
        t.start()


    def notify(self, title, message):
        self.gui.show_message('Sync complete', 'blah')

    def start(self):
        reactor.listenTCP(52045, ServerFactory(self), interface='localhost')

        self.gui.show()

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

if __name__ == '__main__':
    print 'k'
