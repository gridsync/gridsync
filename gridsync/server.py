from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ServerFactory

class MyLineReceiver(LineReceiver):
    def __init__(self):
        pass
    def lineReceived(self, line):
        print line


class MyFactory(ServerFactory):
    protocol = MyLineReceiver


if __name__ == '__main__':
    from twisted.internet import reactor
    reactor.listenTCP(8765, MyFactory())
    reactor.start()
    print 'yo'
    #reactor.run()
else:
    from twisted.application import service, internet
    application = service.Application('dummyserver')
    internet.TCPServer(8765, MyFactory()).setServiceParent(application)
