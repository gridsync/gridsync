#!/usr/bin/env python2

import wx

TRAY_ICON = '../images/systray.png'

def create_menu_item(menu, label, func):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.AppendItem(item)
    return item


class TaskBarIcon(wx.TaskBarIcon):
    def __init__(self):
        super(TaskBarIcon, self).__init__()
        self.set_icon(TRAY_ICON)
        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)
    def CreatePopupMenu(self):
        menu = wx.Menu()
        create_menu_item(menu, 'Open', self.on_open)
        menu.AppendSeparator()
        create_menu_item(menu, 'Exit', self.on_exit)
        return menu
    def set_icon(self, path):
        icon = wx.IconFromBitmap(wx.Bitmap(path))
        self.SetIcon(icon, "Gridsync")
    def on_left_down(self, event):
        print 'Tray icon was left-clicked.'
    def on_open(self, event):
        print 'open'
    def on_exit(self, event):
        wx.CallAfter(self.Destroy)

class App(wx.App):
    def OnInit(self):
        self.SetTopWindow(wx.Frame(None, -1))
        TaskBarIcon()

        return True

def main():
    app = App()
    app.MainLoop()

if __name__ == '__main__':
    main()


