# -*- coding: utf-8 -*-

import logging
import os
import sys

from PyQt5.QtCore import QEvent, QItemSelectionModel, QPoint, QSize, Qt
from PyQt5.QtGui import QCursor, QFont, QIcon, QMovie, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView, QAction, QCheckBox, QFileDialog, QGridLayout,
    QHeaderView, QLabel, QMenu, QMessageBox, QPushButton, QSizePolicy,
    QSpacerItem, QStyledItemDelegate, QTreeView)
from twisted.internet.defer import DeferredList

from gridsync import resource, APP_NAME
from gridsync.desktop import open_path
from gridsync.gui.model import Model
from gridsync.gui.share import InviteSenderDialog
from gridsync.util import humanized_list


class Delegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(Delegate, self).__init__(parent=None)
        self.parent = parent
        self.waiting_movie = QMovie(resource('waiting.gif'))
        self.waiting_movie.setCacheMode(True)
        self.waiting_movie.frameChanged.connect(self.on_frame_changed)
        self.sync_movie = QMovie(resource('sync.gif'))
        self.sync_movie.setCacheMode(True)
        self.sync_movie.frameChanged.connect(self.on_frame_changed)

    def on_frame_changed(self):
        values = self.parent.model().status_dict.values()
        if 0 in values or 1 in values or 99 in values:
            self.parent.viewport().update()
        else:
            self.waiting_movie.setPaused(True)
            self.sync_movie.setPaused(True)

    def paint(self, painter, option, index):
        column = index.column()
        if column == 1:
            pixmap = None
            status = index.data(Qt.UserRole)
            if not status:  # "Loading..."
                self.waiting_movie.setPaused(False)
                pixmap = self.waiting_movie.currentPixmap().scaled(20, 20)
            elif status in (1, 99):  # "Syncing", "Scanning"
                self.sync_movie.setPaused(False)
                pixmap = self.sync_movie.currentPixmap().scaled(20, 20)
            if pixmap:
                point = option.rect.topLeft()
                painter.drawPixmap(QPoint(point.x(), point.y() + 5), pixmap)
                option.rect = option.rect.translated(pixmap.width(), 0)
        super(Delegate, self).paint(painter, option, index)


class View(QTreeView):
    def __init__(self, gui, gateway):  # pylint: disable=too-many-statements
        super(View, self).__init__()
        self.gui = gui
        self.gateway = gateway
        self.invite_sender_dialogs = []
        self.setModel(Model(self))
        self.setItemDelegate(Delegate(self))

        self.setAcceptDrops(True)
        #self.setColumnWidth(0, 150)
        #self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 115)
        self.setColumnWidth(3, 70)
        self.setColumnWidth(4, 10)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setHeaderHidden(True)
        #self.setRootIsDecorated(False)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setFocusPolicy(Qt.NoFocus)
        #font = QFont()
        #font.setPointSize(12)
        #self.header().setFont(font)
        #self.header().setDefaultAlignment(Qt.AlignCenter)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.Stretch)
        #self.header().setSectionResizeMode(2, QHeaderView.Stretch)
        #self.header().setSectionResizeMode(3, QHeaderView.Stretch)
        self.setIconSize(QSize(24, 24))

        self.drop_outline = QLabel(self)
        self.drop_outline.setPixmap(QPixmap(resource('drop_zone_outline.png')))
        self.drop_outline.setScaledContents(True)
        self.drop_outline.setAcceptDrops(True)
        self.drop_outline.installEventFilter(self)

        self.drop_icon = QLabel(self)
        self.drop_icon.setPixmap(QPixmap(resource('upload.png')))
        self.drop_icon.setAlignment(Qt.AlignCenter)
        self.drop_icon.setAcceptDrops(True)
        self.drop_icon.installEventFilter(self)

        self.drop_text = QLabel(self)
        self.drop_text.setText("Drag and drop folders here")
        font = QFont()
        if sys.platform == 'darwin':
            font.setPointSize(18)
        else:
            font.setPointSize(14)
        self.drop_text.setFont(font)
        self.drop_text.setStyleSheet('color: grey')
        self.drop_text.setAlignment(Qt.AlignCenter)
        self.drop_text.setAcceptDrops(True)
        self.drop_text.installEventFilter(self)
        self.drop_text.setSizePolicy(QSizePolicy.Expanding, 0)

        self.drop_subtext = QLabel(self)
        self.drop_subtext.setText(
            "Added folders will sync with {}".format(self.gateway.name))
        self.drop_subtext.setStyleSheet('color: grey')
        self.drop_subtext.setAlignment(Qt.AlignCenter)
        self.drop_subtext.setAcceptDrops(True)
        self.drop_subtext.installEventFilter(self)
        self.drop_subtext.setSizePolicy(QSizePolicy.Expanding, 0)

        self.select_folder_button = QPushButton("Select...", self)
        self.select_folder_button.setAcceptDrops(True)
        self.select_folder_button.installEventFilter(self)
        self.select_folder_button.clicked.connect(self.select_folder)

        layout = QGridLayout(self)
        layout.addWidget(self.drop_outline, 1, 1, 9, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 1, 1)
        layout.addWidget(self.drop_icon, 2, 2, 3, 1)
        layout.addWidget(self.drop_text, 6, 1, 1, 3)
        layout.addWidget(self.drop_subtext, 7, 1, 1, 3)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 8, 1)
        layout.addWidget(self.select_folder_button, 8, 2)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 8, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 9, 1)

        self.doubleClicked.connect(self.on_double_click)
        self.customContextMenuRequested.connect(self.on_right_click)

        self.model().populate()

    def show_drop_label(self, _=None):
        if not self.model().rowCount():
            self.setHeaderHidden(True)
            self.drop_outline.show()
            self.drop_icon.show()
            self.drop_text.show()
            self.drop_subtext.show()
            self.select_folder_button.show()

    def hide_drop_label(self):
        self.setHeaderHidden(False)
        self.drop_outline.hide()
        self.drop_icon.hide()
        self.drop_text.hide()
        self.drop_subtext.hide()
        self.select_folder_button.hide()

    def on_double_click(self, index):
        item = self.model().itemFromIndex(index)
        name = self.model().item(item.row(), 0).text()
        if name in self.gateway.magic_folders:
            open_path(self.gateway.magic_folders[name]['directory'])
        elif self.gateway.remote_magic_folder_exists(name):
            self.select_download_location([name])

    def open_invite_sender_dialog(self, folder_name):
        isd = InviteSenderDialog(self.gateway, self.gui, folder_name)
        self.invite_sender_dialogs.append(isd)  # TODO: Remove on close
        isd.show()

    def restart_gateway(self, _):
        self.gateway.restart()

    def select_download_location(self, folders):
        dest = QFileDialog.getExistingDirectory(
            self, "Select a download destination", os.path.expanduser('~'))
        if not dest:
            return
        tasks = []
        for folder in folders:
            data = self.gateway.remote_magic_folders[folder]
            admin_dircap = data.get('admin_dircap')
            collective_dircap = data['collective_dircap']
            upload_dircap = data['upload_dircap']
            join_code = "{}+{}".format(collective_dircap, upload_dircap)
            path = os.path.join(dest, folder)
            tasks.append(
                self.gateway.create_magic_folder(path, join_code, admin_dircap)
            )
        d = DeferredList(tasks)
        d.addCallback(self.restart_gateway)

    def show_failure(self, failure):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(str(failure.type.__name__))
        msg.setText(str(failure.value))
        logging.error(str(failure))
        msg.exec_()

    def confirm_unlink(self, folders):
        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Question)
        humanized_folders = humanized_list(folders, "folders")
        msgbox.setWindowTitle(
            "Permanently remove {}?".format(humanized_folders))
        if len(folders) == 1:
            msgbox.setText(
                'Are you sure you wish to <b>permanently</b> remove the "{}" '
                'folder?'.format(folders[0]))
        else:
            msgbox.setText(
                "Are you sure you wish to <b>permanently</b> remove {}?"
                .format(humanized_folders))
        msgbox.setInformativeText(
            "Permanently removed folders cannot be restored with your "
            "Recovery Key.")
        msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgbox.setDefaultButton(QMessageBox.No)
        if msgbox.exec_() == QMessageBox.Yes:
            tasks = []
            for folder in folders:
                d = self.gateway.unlink_magic_folder_from_rootcap(folder)
                d.addErrback(self.show_failure)
                tasks.append(d)
                self.model().removeRow(self.model().findItems(folder)[0].row())
            d = DeferredList(tasks)
            d.addCallback(lambda _: self.model().monitor.scan_rootcap())
            d.addCallback(self.show_drop_label)

    def confirm_remove(self, folders):
        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Question)
        humanized_folders = humanized_list(folders, "folders")
        msgbox.setWindowTitle("Remove {}?".format(humanized_folders))
        if len(folders) == 1:
            msgbox.setText(
                'Are you sure you wish to remove the "{}" folder?'.format(
                    folders[0]))
            checkbox = QCheckBox(
                "Allow this folder to be restored later with my Recovery Key")
        else:
            msgbox.setText(
                "Are you sure you wish to remove {}?".format(humanized_folders)
            )
            checkbox = QCheckBox(
                "Allow these folders to be restored later with my Recovery Key"
            )
        msgbox.setInformativeText(
            "Removed folders will remain on your computer but {} will no "
            "longer synchronize their contents with {}.".format(
                APP_NAME, self.gateway.name))
        checkbox.setCheckState(Qt.Checked)
        msgbox.setCheckBox(checkbox)
        msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgbox.setDefaultButton(QMessageBox.Yes)
        if msgbox.exec_() == QMessageBox.Yes:
            tasks = []
            for folder in folders:
                d = self.gateway.remove_magic_folder(folder)
                d.addErrback(self.show_failure)
                tasks.append(d)
                if checkbox.checkState() == Qt.Unchecked:
                    d2 = self.gateway.unlink_magic_folder_from_rootcap(folder)
                    d2.addErrback(self.show_failure)
                    tasks.append(d2)
                self.model().removeRow(self.model().findItems(folder)[0].row())
            d = DeferredList(tasks)
            d.addCallback(lambda _: self.model().monitor.scan_rootcap())
            d.addCallback(self.show_drop_label)

    def open_folders(self, folders):
        for folder in folders:
            folder_info = self.gateway.magic_folders.get(folder)
            if folder_info:
                open_path(folder_info['directory'])

    def deselect_local_folders(self):
        selected = self.selectedIndexes()
        if selected:
            for index in selected:
                item = self.model().itemFromIndex(index)
                folder = self.model().item(item.row(), 0).text()
                if self.gateway.magic_folders.get(folder):
                    self.selectionModel().select(
                        index, QItemSelectionModel.Deselect)

    def deselect_remote_folders(self):
        selected = self.selectedIndexes()
        if selected:
            for index in selected:
                item = self.model().itemFromIndex(index)
                folder = self.model().item(item.row(), 0).text()
                if not self.gateway.magic_folders.get(folder):
                    self.selectionModel().select(
                        index, QItemSelectionModel.Deselect)

    def get_selected_folders(self):
        folders = []
        selected = self.selectedIndexes()
        if selected:
            for index in selected:
                item = self.model().itemFromIndex(index)
                if item.column() == 0:
                    folders.append(item.text())
        return folders

    def on_right_click(self, position):
        if not position:
            position = self.viewport().mapFromGlobal(QCursor().pos())
        cur_item = self.model().itemFromIndex(self.indexAt(position))
        if not cur_item:
            return
        cur_folder = self.model().item(cur_item.row(), 0).text()

        if self.gateway.magic_folders.get(cur_folder):  # is local folder
            selection_is_remote = False
            self.deselect_remote_folders()
        else:
            selection_is_remote = True
            self.deselect_local_folders()

        selected = self.get_selected_folders()
        if not selected:
            selected = [cur_folder]

        menu = QMenu()
        if selection_is_remote:
            download_action = QAction(
                QIcon(resource('download.png')), "Download...")
            download_action.triggered.connect(
                lambda: self.select_download_location(selected))
            menu.addAction(download_action)
            menu.addSeparator()
        open_action = QAction(self.model().icon_folder_gray, "Open")
        open_action.triggered.connect(
            lambda: self.open_folders(selected))
        share_action = QAction(QIcon(resource('share.png')), "Share...")
        share_action.triggered.connect(
            lambda: self.open_invite_sender_dialog(selected))
        remove_action = QAction(QIcon(resource('close.png')), "Remove...")
        menu.addAction(open_action)
        menu.addAction(share_action)
        menu.addSeparator()
        menu.addAction(remove_action)
        if selection_is_remote:
            open_action.setEnabled(False)
            share_action.setEnabled(False)
            remove_action.triggered.connect(
                lambda: self.confirm_unlink(selected))
        else:
            for folder in selected:
                if not self.gateway.magic_folders[folder]['admin_dircap']:
                    share_action.setEnabled(False)
                    share_action.setText("Share (disabled; no admin access)")
            remove_action.triggered.connect(
                lambda: self.confirm_remove(selected))
        menu.exec_(self.viewport().mapToGlobal(position))

    def add_new_folder(self, path):
        basename = os.path.basename(os.path.normpath(path))
        if self.gateway.magic_folder_exists(basename):
            QMessageBox.critical(
                self,
                "Folder already exists",
                'You already belong to a folder named "{}" on {}. Please '
                'rename it and try again.'.format(basename, self.gateway.name)
            )
            return
        self.hide_drop_label()
        self.model().add_folder(path)
        self.gateway.create_magic_folder(path)

    def add_folders(self, paths):
        paths_to_add = []
        for path in paths:
            basename = os.path.basename(os.path.normpath(path))
            if not os.path.isdir(path):
                QMessageBox.critical(
                    self,
                    "Cannot add {}.".format(basename),
                    "Cannot add '{}'.\n\n{} currently only supports uploading "
                    "and syncing folders, and not individual files.".format(
                        basename, APP_NAME)
                )
            elif self.gateway.magic_folder_exists(basename):
                QMessageBox.critical(
                    self,
                    "Folder already exists",
                    'You already belong to a folder named "{}" on {}. Please '
                    'rename it and try again.'.format(basename,
                                                      self.gateway.name)
                )
            else:
                paths_to_add.append(path)
        if paths_to_add:
            self.hide_drop_label()
            tasks = []
            for path in paths_to_add:
                self.model().add_folder(path)
                tasks.append(self.gateway.create_magic_folder(path))
            d = DeferredList(tasks)
            d.addCallback(self.restart_gateway)

    def select_folder(self):
        dialog = QFileDialog(self, "Please select a folder")
        dialog.setDirectory(os.path.expanduser('~'))
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly)
        if dialog.exec_():
            self.add_folders(dialog.selectedFiles())

    def dragEnterEvent(self, event):  # pylint: disable=no-self-use
        logging.debug(event)
        if event.mimeData().hasUrls:
            event.accept()

    def dragLeaveEvent(self, event):  # pylint: disable=no-self-use
        logging.debug(event)
        event.accept()

    def dragMoveEvent(self, event):  # pylint: disable=no-self-use
        logging.debug(event)
        if event.mimeData().hasUrls:
            event.accept()

    def dropEvent(self, event):
        logging.debug(event)
        if event.mimeData().hasUrls:
            event.accept()
            paths = []
            for url in event.mimeData().urls():
                paths.append(url.toLocalFile())
            self.add_folders(paths)

    def eventFilter(self, obj, event):  # pylint: disable=unused-argument
        if event.type() == QEvent.DragEnter:
            self.dragEnterEvent(event)
            return True
        if event.type() == QEvent.DragLeave:
            self.dragLeaveEvent(event)
            return True
        if event.type() == QEvent.DragMove:
            self.dragMoveEvent(event)
            return True
        if event.type() == QEvent.Drop:
            self.dropEvent(event)
            return True
        return False
