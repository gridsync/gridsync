from systray import SystemTrayIcon
from main_window import MainWindow

class Gui():
    def __init__(self, parent):
        self.tray = SystemTrayIcon(parent)
        #self.mw = MainWindow()

    def show(self):
        self.tray.show()
        #self.mw.show()

    def start_animation(self):
        self.tray.start_animation()

    def stop_animation(self):
        self.tray.stop_animation()

    def show_message(self, title, text):
        self.tray.show_message(title, text)
