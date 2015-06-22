from systray import SystemTrayIcon
from main_window import MainWindow

class Gui():
    def __init__(self):
        self.tray = SystemTrayIcon()
        self.mw = MainWindow()

    def show(self):
        self.tray.show()
        self.mw.show()
