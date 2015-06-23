import threading

def do_pause():
    print 'k'
    t = threading.Timer(1.0, do_pause)
    t.setDaemon(True)
    t.start()
    print 'yo'

#t = threading.Timer(1.0, do_pause)
#t.setDaemon(True)
#t.start


do_pause()

while 1:
    pass
