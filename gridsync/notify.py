import sys


def notify(title, text):
    if sys.platform == 'darwin':
        from Foundation import NSDate
        from objc import lookUpClass
        NSUserNotification = lookUpClass('NSUserNotification')
        NSUserNotificationCenter = lookUpClass('NSUserNotificationCenter')
        n = NSUserNotification.alloc().init()
        n.setTitle_(title)
        n.setInformativeText_(text)
        n.setDeliveryDate_(NSDate.dateWithTimeInterval_sinceDate_(0, NSDate.date()))
        NSUserNotificationCenter.defaultUserNotificationCenter().scheduleNotification_(n)
    elif sys.platform == 'linux2':
        import notify2
        notify2.init('Gridsync')
        n = notify2.Notification(title, text, "notification-message-im")
        n.show()

notify('test', 'testing')
