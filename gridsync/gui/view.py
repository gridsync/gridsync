# -*- coding: utf-8 -*-

import logging
import os
import sys

from PyQt5.QtCore import QEvent, QItemSelectionModel, QPoint, QSize, Qt
from PyQt5.QtGui import QColor, QCursor, QIcon, QMovie, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStyledItemDelegate,
    QTreeView,
)
from twisted.internet.defer import DeferredList, inlineCallbacks

from gridsync import resource, APP_NAME, settings
from gridsync.desktop import open_path
from gridsync.gui.font import Font
from gridsync.gui.model import Model
from gridsync.gui.share import InviteSenderDialog
from gridsync.monitor import MagicFolderChecker
from gridsync.msg import error
from gridsync.util import humanized_list


class Delegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(Delegate, self).__init__(parent=None)
        self.parent = parent
        self.waiting_movie = QMovie(resource("waiting.gif"))
        self.waiting_movie.setCacheMode(True)
        self.waiting_movie.frameChanged.connect(self.on_frame_changed)
        self.sync_movie = QMovie(resource("sync.gif"))
        self.sync_movie.setCacheMode(True)
        self.sync_movie.frameChanged.connect(self.on_frame_changed)

    def on_frame_changed(self):
        values = self.parent.model().status_dict.values()
        if (
            MagicFolderChecker.LOADING in values
            or MagicFolderChecker.SYNCING in values
            or MagicFolderChecker.SCANNING in values
        ):
            self.parent.viewport().update()
        else:
            self.waiting_movie.setPaused(True)
            self.sync_movie.setPaused(True)

    def paint(self, painter, option, index):
        column = index.column()
        if column == 1:
            pixmap = None
            status = index.data(Qt.UserRole)
            if status == MagicFolderChecker.LOADING:
                self.waiting_movie.setPaused(False)
                pixmap = self.waiting_movie.currentPixmap().scaled(
                    20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            elif status in (
                MagicFolderChecker.SYNCING,
                MagicFolderChecker.SCANNING,
            ):
                self.sync_movie.setPaused(False)
                pixmap = self.sync_movie.currentPixmap().scaled(
                    20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
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
        self._rescan_required = False
        self._restart_required = False
        self.setModel(Model(self))
        self.setItemDelegate(Delegate(self))

        self.setAcceptDrops(True)
        # self.setColumnWidth(0, 150)
        # self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 115)
        self.setColumnWidth(3, 70)
        self.setColumnWidth(4, 10)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setHeaderHidden(True)
        # self.setRootIsDecorated(False)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setFocusPolicy(Qt.NoFocus)
        # font = QFont()
        # font.setPointSize(12)
        # self.header().setFont(font)
        # self.header().setDefaultAlignment(Qt.AlignCenter)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.Stretch)
        # self.header().setSectionResizeMode(2, QHeaderView.Stretch)
        # self.header().setSectionResizeMode(3, QHeaderView.Stretch)
        self.setIconSize(QSize(24, 24))

        # XXX Should match the result of subtracting top from left margin from
        # CentralWidget's folders_views[gateway].layout().getContentsMargins()
        # but since this object's enclosing widget/layout won't appear in the
        # folders_views dict until after this __init__() call completes, set
        # the value "manually" instead.
        self.dropzone_top_margin = 0 if sys.platform == "darwin" else 11

        self.drop_icon = QLabel(self)
        self.drop_icon.setPixmap(QPixmap(resource("upload.png")))
        self.drop_icon.setAlignment(Qt.AlignCenter)
        self.drop_icon.setAcceptDrops(True)
        self.drop_icon.installEventFilter(self)

        self.drop_text = QLabel(self)
        self.drop_text.setText("Drag and drop folders here")
        self.drop_text.setFont(Font(14))
        self.drop_text.setStyleSheet("color: grey")
        self.drop_text.setAlignment(Qt.AlignCenter)
        self.drop_text.setAcceptDrops(True)
        self.drop_text.installEventFilter(self)
        self.drop_text.setSizePolicy(QSizePolicy.Expanding, 0)

        self.drop_subtext = QLabel(self)
        self.drop_subtext.setText(
            "Added folders will sync with {}".format(self.gateway.name)
        )
        self.drop_subtext.setFont(Font(10))
        self.drop_subtext.setStyleSheet("color: grey")
        self.drop_subtext.setAlignment(Qt.AlignCenter)
        self.drop_subtext.setAcceptDrops(True)
        self.drop_subtext.installEventFilter(self)
        self.drop_subtext.setSizePolicy(QSizePolicy.Expanding, 0)

        self.select_folder_button = QPushButton("Select...", self)
        self.select_folder_button.setAcceptDrops(True)
        self.select_folder_button.installEventFilter(self)
        self.select_folder_button.clicked.connect(self.select_folder)

        layout = QGridLayout(self)
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
            self.drop_icon.show()
            self.drop_text.show()
            self.drop_subtext.show()
            self.select_folder_button.show()

    def hide_drop_label(self):
        self.setHeaderHidden(False)
        self.drop_icon.hide()
        self.drop_text.hide()
        self.drop_subtext.hide()
        self.select_folder_button.hide()

    def on_double_click(self, index):
        item = self.model().itemFromIndex(index)
        name = self.model().item(item.row(), 0).text()
        if name in self.gateway.magic_folders:
            try:
                open_path(self.gateway.magic_folders[name]["directory"])
            except KeyError:
                pass
        elif self.gateway.remote_magic_folder_exists(name):
            self.select_download_location([name])

    def open_invite_sender_dialog(self, folder_name):
        isd = InviteSenderDialog(self.gateway, self.gui, folder_name)
        self.invite_sender_dialogs.append(isd)  # TODO: Remove on close
        isd.show()

    @inlineCallbacks
    def maybe_rescan_rootcap(self, _):
        if self._rescan_required:
            self._rescan_required = False
            logging.debug("A rescan was scheduled; rescanning...")
            yield self.gateway.monitor.scan_rootcap()
            self.show_drop_label()
        else:
            logging.debug("No rescans were scheduled; not rescanning")

    @inlineCallbacks
    def maybe_restart_gateway(self, _):
        if self._restart_required:
            self._restart_required = False
            logging.debug("A restart was scheduled; restarting...")
            yield self.gateway.restart()
        else:
            logging.debug("No restarts were scheduled; not restarting")

    @inlineCallbacks
    def download_folder(self, folder_name, dest):
        try:
            yield self.gateway.restore_magic_folder(folder_name, dest)
        except Exception as e:  # pylint: disable=broad-except
            logging.error("%s: %s", type(e).__name__, str(e))
            error(
                self,
                'Error downloading folder "{}"'.format(folder_name),
                'An exception was raised when downloading the "{}" folder:\n\n'
                "{}: {}".format(folder_name, type(e).__name__, str(e)),
            )
            return
        self._restart_required = True
        logging.debug(
            'Successfully joined folder "%s"; scheduled restart', folder_name
        )

    def select_download_location(self, folders):
        dest = QFileDialog.getExistingDirectory(
            self, "Select a download destination", os.path.expanduser("~")
        )
        if not dest:
            return
        tasks = []
        for folder in folders:
            tasks.append(self.download_folder(folder, dest))
        d = DeferredList(tasks)
        d.addCallback(self.maybe_restart_gateway)

    def show_failure(self, failure):
        logging.error("%s: %s", str(failure.type.__name__), str(failure.value))
        error(self, str(failure.type.__name__), str(failure.value))

    @inlineCallbacks
    def unlink_folder(self, folder_name):
        try:
            yield self.gateway.unlink_magic_folder_from_rootcap(folder_name)
        except Exception as e:  # pylint: disable=broad-except
            logging.error("%s: %s", type(e).__name__, str(e))
            error(
                self,
                'Error unlinking folder "{}"'.format(folder_name),
                'An exception was raised when unlinking the "{}" folder:\n\n'
                "{}: {}\n\nPlease try again later.".format(
                    folder_name, type(e).__name__, str(e)
                ),
            )
            return
        self.model().remove_folder(folder_name)
        self._rescan_required = True
        logging.debug(
            'Successfully unlinked folder "%s"; scheduled rescan', folder_name
        )

    def confirm_unlink(self, folders):
        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Question)
        humanized_folders = humanized_list(folders, "folders")
        msgbox.setWindowTitle(
            "Permanently remove {}?".format(humanized_folders)
        )
        if len(folders) == 1:
            msgbox.setText(
                'Are you sure you wish to <b>permanently</b> remove the "{}" '
                "folder?".format(folders[0])
            )
        else:
            msgbox.setText(
                "Are you sure you wish to <b>permanently</b> remove {}?".format(
                    humanized_folders
                )
            )
        msgbox.setInformativeText(
            "Permanently removed folders cannot be restored with your "
            "Recovery Key."
        )
        msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgbox.setDefaultButton(QMessageBox.No)
        if msgbox.exec_() == QMessageBox.Yes:
            tasks = []
            for folder in folders:
                tasks.append(self.unlink_folder(folder))
            d = DeferredList(tasks)
            d.addCallback(self.maybe_rescan_rootcap)

    @inlineCallbacks
    def remove_folder(self, folder_name, unlink=False):
        try:
            yield self.gateway.remove_magic_folder(folder_name)
        except Exception as e:  # pylint: disable=broad-except
            logging.error("%s: %s", type(e).__name__, str(e))
            error(
                self,
                'Error removing folder "{}"'.format(folder_name),
                'An exception was raised when removing the "{}" folder:\n\n'
                "{}: {}\n\nPlease try again later.".format(
                    folder_name, type(e).__name__, str(e)
                ),
            )
            return
        self.model().remove_folder(folder_name)
        self._restart_required = True
        logging.debug(
            'Successfully removed folder "%s"; scheduled restart', folder_name
        )
        if unlink:
            yield self.unlink_folder(folder_name)

    def confirm_stop_syncing(self, folders):
        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Question)
        humanized_folders = humanized_list(folders, "folders")
        msgbox.setWindowTitle("Stop syncing {}?".format(humanized_folders))
        if len(folders) == 1:
            msgbox.setText(
                'Are you sure you wish to stop syncing the "{}" folder?'.format(
                    folders[0]
                )
            )
            msgbox.setInformativeText(
                "This folder will remain on your computer but it will no "
                "longer synchronize automatically with {}.".format(
                    self.gateway.name
                )
            )
            checkbox = QCheckBox(
                "Keep a backup copy of this folder on {}".format(
                    self.gateway.name
                )
            )
        else:
            msgbox.setText(
                "Are you sure you wish to stop syncing {}?".format(
                    humanized_folders
                )
            )
            msgbox.setInformativeText(
                "These folders will remain on your computer but they will no "
                "longer synchronize automatically with {}.".format(
                    self.gateway.name
                )
            )
            checkbox = QCheckBox(
                "Keep backup copies of these folders on {}".format(
                    self.gateway.name
                )
            )
        checkbox.setCheckState(Qt.Unchecked)
        msgbox.setCheckBox(checkbox)
        msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgbox.setDefaultButton(QMessageBox.Yes)
        if msgbox.exec_() == QMessageBox.Yes:
            tasks = []
            if checkbox.checkState() == Qt.Checked:
                for folder in folders:
                    tasks.append(self.remove_folder(folder, unlink=False))
            else:
                for folder in folders:
                    tasks.append(self.remove_folder(folder, unlink=True))
            d = DeferredList(tasks)
            d.addCallback(self.maybe_rescan_rootcap)
            d.addCallback(self.maybe_restart_gateway)

    def open_folders(self, folders):
        for folder in folders:
            folder_info = self.gateway.magic_folders.get(folder)
            if folder_info:
                try:
                    open_path(folder_info["directory"])
                except KeyError:
                    pass

    def deselect_local_folders(self):
        selected = self.selectedIndexes()
        if selected:
            for index in selected:
                item = self.model().itemFromIndex(index)
                folder = self.model().item(item.row(), 0).text()
                if self.gateway.magic_folders.get(folder):
                    self.selectionModel().select(
                        index, QItemSelectionModel.Deselect
                    )

    def deselect_remote_folders(self):
        selected = self.selectedIndexes()
        if selected:
            for index in selected:
                item = self.model().itemFromIndex(index)
                folder = self.model().item(item.row(), 0).text()
                if not self.gateway.magic_folders.get(folder):
                    self.selectionModel().select(
                        index, QItemSelectionModel.Deselect
                    )

    def get_selected_folders(self):
        folders = []
        selected = self.selectedIndexes()
        if selected:
            for index in selected:
                item = self.model().itemFromIndex(index)
                if item.column() == 0:
                    folders.append(item.text())
        return folders

    def on_right_click(self, position):  # noqa: max-complexity
        if not position:  # From left-click on "Action" button
            position = self.viewport().mapFromGlobal(QCursor().pos())
            self.deselect_remote_folders()
            self.deselect_local_folders()
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
                QIcon(resource("download.png")), "Download..."
            )
            download_action.triggered.connect(
                lambda: self.select_download_location(selected)
            )
            menu.addAction(download_action)
            menu.addSeparator()
        open_action = QAction(self.model().icon_folder_gray, "Open")
        open_action.triggered.connect(lambda: self.open_folders(selected))

        share_menu = QMenu()
        share_menu.setIcon(QIcon(resource("laptop.png")))
        share_menu.setTitle("Sync with device")  # XXX Rephrase?
        invite_action = QAction(
            QIcon(resource("invite.png")), "Create Invite Code..."
        )
        invite_action.triggered.connect(
            lambda: self.open_invite_sender_dialog(selected)
        )
        share_menu.addAction(invite_action)

        remove_action = QAction(
            QIcon(resource("close.png")), "Remove from Recovery Key..."
        )
        menu.addAction(open_action)
        features_settings = settings.get("features")
        if features_settings:
            invites_setting = features_settings.get("invites")
            if invites_setting and invites_setting.lower() != "false":
                menu.addMenu(share_menu)
        else:
            menu.addMenu(share_menu)
        menu.addSeparator()
        menu.addAction(remove_action)
        if selection_is_remote:
            open_action.setEnabled(False)
            share_menu.setEnabled(False)
            remove_action.triggered.connect(
                lambda: self.confirm_unlink(selected)
            )
        else:
            for folder in selected:
                if not self.gateway.magic_folders[folder]["admin_dircap"]:
                    share_menu.setEnabled(False)
                    share_menu.setTitle(
                        "Sync with device (disabled; no admin access)"
                    )
            remove_action.setText("Stop syncing...")
            remove_action.triggered.connect(
                lambda: self.confirm_stop_syncing(selected)
            )
        menu.exec_(self.viewport().mapToGlobal(position))

    @inlineCallbacks
    def add_folder(self, path):
        path = os.path.realpath(path)
        self.model().add_folder(path)
        folder_name = os.path.basename(path)
        try:
            yield self.gateway.create_magic_folder(path)
        except Exception as e:  # pylint: disable=broad-except
            logging.error("%s: %s", type(e).__name__, str(e))
            error(
                self,
                'Error adding folder "{}"'.format(folder_name),
                'An exception was raised when adding the "{}" folder:\n\n'
                "{}: {}\n\nPlease try again later.".format(
                    folder_name, type(e).__name__, str(e)
                ),
            )
            self.model().remove_folder(folder_name)
            return
        self._restart_required = True
        logging.debug(
            'Successfully added folder "%s"; scheduled restart', folder_name
        )

    def add_folders(self, paths):
        paths_to_add = []
        for path in paths:
            basename = os.path.basename(os.path.normpath(path))
            if not os.path.isdir(path):
                error(
                    self,
                    'Cannot add "{}".'.format(basename),
                    "{} only supports uploading and syncing folders,"
                    " and not individual files.".format(APP_NAME),
                )
            elif self.gateway.magic_folder_exists(basename):
                error(
                    self,
                    "Folder already exists",
                    'You already belong to a folder named "{}" on {}. Please '
                    "rename it and try again.".format(
                        basename, self.gateway.name
                    ),
                )
            else:
                paths_to_add.append(path)
        if paths_to_add:
            self.hide_drop_label()
            tasks = []
            for path in paths_to_add:
                tasks.append(self.add_folder(path))
            d = DeferredList(tasks)
            d.addCallback(self.maybe_restart_gateway)

    def select_folder(self):
        dialog = QFileDialog(self, "Please select a folder")
        dialog.setDirectory(os.path.expanduser("~"))
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

    def paintEvent(self, event):
        if not self.model().rowCount():
            self.show_drop_label()
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor(128, 128, 128), 5)
            pen.setDashPattern([1, 2.91])
            painter.setPen(pen)
            geometry = self.geometry()
            painter.drawRect(
                geometry.x(),
                geometry.y() + self.dropzone_top_margin,
                geometry.width() - 24,
                geometry.height() - 24,
            )
        super().paintEvent(event)
