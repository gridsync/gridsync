#!/usr/bin/env python2
# vim:fileencoding=utf-8:ft=python

from twisted.internet.protocol import Protocol, ServerFactory
from twisted.internet import reactor


class ServerProtocol(Protocol):

    def dataReceived(self, data):
        print("Received: " + data)
        command = data.lower()
        if command.startswith('gridsync:'):
            print('got gridsync uri')
        elif command == "stop" or command == "quit":
            reactor.stop()
        else:
            print("Invalid command")
        #self.transport.loseConnection()


def start():
    factory = ServerFactory()
    factory.protocol = ServerProtocol
    reactor.listenTCP(52045, factory, interface='localhost')
    #XXX move Config here?
    reactor.run()

