# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING

from qtpy.QtCore import (
    QEvent,
    QItemSelectionModel,
    QModelIndex,
    QObject,
    QPoint,
    QSize,
    Qt,
    QTimer,
)
from qtpy.QtGui import (
    QColor,
    QCursor,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QIcon,
    QMovie,
    QPainter,
    QPaintEvent,
    QPen,
    QShowEvent,
)
from qtpy.QtWidgets import (
    QAbstractItemView,
    QAction,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QHeaderView,
    QMenu,
    QMessageBox,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeView,
)
from twisted.internet.defer import (
    Deferred,
    DeferredList,
    ensureDeferred,
    inlineCallbacks,
)
from twisted.python.failure import Failure

from gridsync import APP_NAME, features, resource
from gridsync.desktop import open_path
from gridsync.gui.font import Font
from gridsync.gui.magic_folder import (
    MagicFolderInviteDialog,
    MagicFolderInvitesModel,
    MagicFolderJoinDialog,
)
from gridsync.gui.model import Model
from gridsync.gui.pixmap import Pixmap
from gridsync.gui.share import InviteSenderDialog
from gridsync.gui.widgets import ClickableLabel, HSpacer, VSpacer
from gridsync.magic_folder import MagicFolderStatus
from gridsync.msg import error
from gridsync.tahoe import Tahoe
from gridsync.types_ import TwistedDeferred
from gridsync.util import humanized_list, traceback

if TYPE_CHECKING:
    from gridsync.gui import AbstractGui


class View(QTreeView):
    def __init__(
        self, gui: AbstractGui, gateway: Tahoe
    ) -> None:  # pylint: disable=too-many-statements
        super().__init__()
        self.gui = gui
        self.gateway = gateway
        self.recovery_prompt_shown: bool = False
        self.invite_sender_dialogs: list = []
        self.open_dialogs: set = set()
        self.magic_folder_invites_model = MagicFolderInvitesModel()
        self._model = Model(self)
        self.setModel(self._model)
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

        self.add_folder_icon = ClickableLabel(self)
        self.add_folder_icon.setPixmap(Pixmap("folder-plus-outline.png", 100))
        self.add_folder_icon.setAlignment(Qt.AlignCenter)
        self.add_folder_icon.setAcceptDrops(True)
        self.add_folder_icon.installEventFilter(self)

        self.add_folder_label = ClickableLabel(self)
        self.add_folder_label.setText(
            "Add a folder to sync with\n{}".format(self.gateway.name)
        )
        self.add_folder_label.setFont(Font(12))
        self.add_folder_label.setStyleSheet("color: grey")
        self.add_folder_label.setAlignment(Qt.AlignCenter)
        self.add_folder_label.setAcceptDrops(True)
        self.add_folder_label.installEventFilter(self)

        layout = QGridLayout(self)
        layout.addItem(VSpacer(), 1, 1)
        layout.addWidget(self.add_folder_icon, 2, 2)
        layout.addItem(HSpacer(), 3, 1)
        layout.addWidget(self.add_folder_label, 3, 2)
        layout.addItem(HSpacer(), 3, 3)
        layout.addItem(VSpacer(), 4, 1)

        self.add_folder_icon.clicked.connect(self.select_folder)
        self.add_folder_label.clicked.connect(self.select_folder)

        self.doubleClicked.connect(self.on_double_click)
        self.customContextMenuRequested.connect(self.on_right_click)

        self.gateway.monitor.zkaps_available.connect(self._create_rootcap)
        self.gateway.monitor.connected.connect(self.maybe_prompt_for_recovery)

    def get_model(self) -> Model:
        # This custom getter exists primarily to inform mypy that we
        # always/only expect this View to use a Model -- and not some
        # other non-Model type. In other words, this is a stricter
        # version of the model() method inherited from
        # QAbstractItemView.
        return self._model

    @inlineCallbacks
    def _create_rootcap(self) -> TwistedDeferred[None]:
        # There's probably a better place/module for this...
        try:
            yield Deferred.fromCoroutine(self.gateway.create_rootcap())
        except Exception as exc:  # pylint: disable=broad-except
            error(
                self,
                "Error creating rootcap",
                f"Could not create rootcap: {str(exc)}",
                traceback(exc),
            )

    def maybe_prompt_for_recovery(self) -> None:
        if (
            self.isVisible()
            and self.gateway.state == Tahoe.STARTED
            and self.gateway.rootcap_manager.get_rootcap()
            and not self.gateway.recovery_key_exported
            and not self.recovery_prompt_shown
        ):
            if (
                self.gateway.monitor.zkap_checker.zkaps_total
                or not self.gateway.zkap_auth_required
            ):
                self.recovery_prompt_shown = True
                self.gui.main_window.prompt_for_export(self.gateway)

    def show_drop_label(self, _: object = None) -> None:
        if not self.get_model().rowCount():
            self.setHeaderHidden(True)
            self.add_folder_icon.show()
            self.add_folder_label.show()

    def hide_drop_label(self) -> None:
        self.setHeaderHidden(False)
        self.add_folder_icon.hide()
        self.add_folder_label.hide()

    def on_double_click(self, index: QModelIndex) -> None:
        item = self.get_model().itemFromIndex(index)
        name = self.get_model().item(item.row(), 0).text()
        if self.gateway.magic_folder.folder_is_local(name):
            directory = self.gateway.magic_folder.get_directory(name)
            if directory:
                open_path(directory)
        elif self.gateway.magic_folder.folder_is_remote(name):
            self.select_download_location([name])

    def open_invite_sender_dialog(self, folder_names: list) -> None:
        isd = InviteSenderDialog(self.gateway, self.gui, folder_names)
        self.invite_sender_dialogs.append(isd)  # TODO: Remove on close
        isd.show()

    async def _cancel_invite(self, folder_name: str, id_: str) -> None:
        d = self.magic_folder_invites_model.get_invite_wait_deferred(id_)
        if d is not None:
            self.magic_folder_invites_model.set_invite_wait_deferred(id_, None)
            d.cancel()
        try:
            await self.gateway.magic_folder.invite_cancel(folder_name, id_)
        except Exception as e:  # pylint: disable=broad-except
            logging.error("%s: %s", type(e).__name__, str(e))
            try:
                reason = str(e.reason)  # type: ignore[attr-defined]
            except AttributeError:
                reason = f"{type(e).__name__}: {str(e)}"
            error(
                self,
                f'Error cancelling invite to "{folder_name}"',
                f'An error occurred when cancelling the invite "{id_}" '
                f'to the "{folder_name}" folder: {reason}',
                traceback(e),
            )

    async def _do_invite(
        self,
        dialog: MagicFolderInviteDialog,
        folder_name: str,
        participant_name: str,
        mode: str,
    ) -> None:
        inv = await self.gateway.magic_folder.invite(
            folder_name, participant_name, mode
        )
        id_ = inv["id"]
        wormhole_code = inv["wormhole-code"]
        self.magic_folder_invites_model.add_invite(id_, wormhole_code)
        self.magic_folder_invites_model.set_dialog(id_, dialog)
        logging.debug("Created Magic-Folder invite: %s", inv)  # XXX
        dialog.cancel_requested.connect(
            lambda: ensureDeferred(self._cancel_invite(folder_name, id_))
        )
        dialog.show_code(wormhole_code)
        d = ensureDeferred(
            self.gateway.magic_folder.invite_wait(folder_name, id_)
        )
        self.magic_folder_invites_model.set_invite_wait_deferred(id_, d)
        try:
            result = await d
        except Exception as e:
            if (
                self.magic_folder_invites_model.get_invite_wait_deferred(id_)
                is None
            ):
                # The invite was cancelled
                return
            raise e
        if result["success"] is True:
            dialog.show_success()

    async def _try_invite(
        self,
        dialog: MagicFolderInviteDialog,
        folder_name: str,
        participant_name: str,
        mode: str,
    ) -> None:
        try:
            await self._do_invite(dialog, folder_name, participant_name, mode)
        except Exception as e:  # pylint: disable=broad-except
            logging.error("%s: %s", type(e).__name__, str(e))
            try:
                reason = str(e.reason)  # type: ignore[attr-defined]
            except AttributeError:
                reason = f"{type(e).__name__}: {str(e)}"
            error(
                self,
                f"Error inviting {participant_name} to {folder_name}",
                f'An error occurred when inviting "{participant_name}" to '
                f'the "{folder_name}" folder: {reason}',
                traceback(e),
            )

    def open_magic_folder_invite_dialog(self, folder_name: str) -> None:
        logging.debug("Creating Magic-Folder invite for %s...", folder_name)
        dialog = MagicFolderInviteDialog()
        # To prevent the dialog from getting garbage-collected
        self.open_dialogs.add(dialog)  # TODO: Remove on close?
        dialog.set_folder_name(folder_name)
        dialog.form_filled.connect(
            lambda participant_name, mode: ensureDeferred(
                self._try_invite(dialog, folder_name, participant_name, mode)
            )
        )
        dialog.show()

    async def _do_join(
        self,
        dialog: MagicFolderJoinDialog,
        folder_name: str,
        invite_code: str,
        local_path: str,
    ) -> None:
        result = await self.gateway.magic_folder.join(
            folder_name, invite_code, local_path
        )
        if result["success"] is True:
            dialog.show_success()

    async def _try_join(
        self,
        dialog: MagicFolderJoinDialog,
        folder_name: str,
        invite_code: str,
        local_path: str,
    ) -> None:
        try:
            await self._do_join(dialog, folder_name, invite_code, local_path)
        except Exception as e:  # pylint: disable=broad-except
            logging.error("%s: %s", type(e).__name__, str(e))
            try:
                reason = str(e.reason)  # type: ignore[attr-defined]
            except AttributeError:
                reason = f"{type(e).__name__}: {str(e)}"
            error(
                self,
                f"Error joining {folder_name}",
                f'An error occurred when joining the "{folder_name}" folder: '
                f"{reason}",
                traceback(e),
            )

    def open_magic_folder_join_dialog(self) -> None:
        dialog = MagicFolderJoinDialog()
        # To prevent the dialog from getting garbage-collected
        self.open_dialogs.add(dialog)  # TODO: Remove on close?
        dialog.form_filled.connect(
            lambda folder_name, invite_code, local_path: ensureDeferred(
                self._try_join(dialog, folder_name, invite_code, local_path)
            )
        )
        dialog.show()

    @inlineCallbacks
    def download_folder(
        self, folder_name: str, dest: str
    ) -> TwistedDeferred[None]:
        try:
            yield Deferred.fromCoroutine(
                self.gateway.magic_folder.restore_folder_backup(
                    folder_name, os.path.join(dest, folder_name)
                )
            )
        except Exception as e:  # pylint: disable=broad-except
            logging.error("%s: %s", type(e).__name__, str(e))
            try:
                reason = str(e.reason)  # type: ignore[attr-defined]
            except AttributeError:
                reason = f"{type(e).__name__}: {str(e)}"
            error(
                self,
                f'Error downloading "{folder_name}" folder',
                f'An error occurred when downloading the "{folder_name}" '
                f"folder: {reason}",
                traceback(e),
            )
            return
        logging.debug('Successfully joined folder "%s"', folder_name)

    def select_download_location(self, folders: list) -> None:
        dest = QFileDialog.getExistingDirectory(
            self, "Select a download destination", os.path.expanduser("~")
        )
        if not dest:
            return
        tasks = []
        for folder in folders:
            tasks.append(self.download_folder(folder, dest))
        DeferredList(tasks)  # XXX

    def show_failure(self, failure: Failure) -> None:
        logging.error("%s: %s", str(failure.type.__name__), str(failure.value))
        error(self, str(failure.type.__name__), str(failure.value))

    @inlineCallbacks
    def remove_folder_backup(self, folder_name: str) -> TwistedDeferred[None]:
        try:
            yield Deferred.fromCoroutine(
                self.gateway.magic_folder.remove_folder_backup(folder_name)
            )
        except Exception as e:  # pylint: disable=broad-except
            logging.error("%s: %s", type(e).__name__, str(e))
            try:
                reason = str(e.reason)  # type: ignore[attr-defined]
            except AttributeError:
                reason = f"{type(e).__name__}: {str(e)}"
            error(
                self,
                f'Error removing "{folder_name}" backup',
                f'An error occurred when removing the "{folder_name}" backup: '
                f"{reason}\n\nPlease try again later.",
                traceback(e),
            )
            return
        self.get_model().remove_folder(folder_name)
        logging.debug('Successfully removed "%s" folder backup', folder_name)

    def confirm_remove_folder_backup(self, folders: list) -> None:
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
                tasks.append(self.remove_folder_backup(folder))
            # XXX Something should wait on this.
            DeferredList(tasks)

    @inlineCallbacks
    def remove_folder(
        self, folder_name: str, remove_backup: bool = False
    ) -> TwistedDeferred[None]:
        try:
            yield Deferred.fromCoroutine(
                self.gateway.magic_folder.leave_folder(
                    folder_name, missing_ok=True
                )
            )
        except Exception as e:  # pylint: disable=broad-except
            logging.error("%s: %s", type(e).__name__, str(e))
            try:
                reason = str(e.reason)  # type: ignore[attr-defined]
            except AttributeError:
                reason = f"{type(e).__name__}: {str(e)}"
            error(
                self,
                f'Error removing "{folder_name}" folder',
                f'An error occurred when removing the "{folder_name}" folder: '
                f"{reason}\n\nPlease try again later.",
                traceback(e),
            )
            return
        self.get_model().on_folder_removed(folder_name)
        logging.debug('Successfully removed folder "%s"', folder_name)
        if remove_backup:
            yield self.remove_folder_backup(folder_name)

    def confirm_stop_syncing(self, folders: list) -> None:
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
                    tasks.append(
                        self.remove_folder(folder, remove_backup=False)
                    )
            else:
                for folder in folders:
                    tasks.append(
                        self.remove_folder(folder, remove_backup=True)
                    )
            DeferredList(tasks)

    def open_folders(self, folders: list) -> None:
        for folder_name in folders:
            directory = self.gateway.magic_folder.get_directory(folder_name)
            if directory:
                open_path(directory)

    def deselect_local_folders(self) -> None:
        selected = self.selectedIndexes()
        if selected:
            for index in selected:
                item = self.get_model().itemFromIndex(index)
                folder = self.get_model().item(item.row(), 0).text()
                if self.gateway.magic_folder.folder_is_local(folder):
                    self.selectionModel().select(
                        index, QItemSelectionModel.Deselect
                    )

    def deselect_remote_folders(self) -> None:
        selected = self.selectedIndexes()
        if selected:
            for index in selected:
                item = self.get_model().itemFromIndex(index)
                folder = self.get_model().item(item.row(), 0).text()
                if not self.gateway.magic_folder.folder_is_local(folder):
                    self.selectionModel().select(
                        index, QItemSelectionModel.Deselect
                    )

    def get_selected_folders(self) -> list:
        folders = []
        selected = self.selectedIndexes()
        if selected:
            for index in selected:
                item = self.get_model().itemFromIndex(index)
                if item.column() == 0:
                    folders.append(item.text())
        return folders

    def on_right_click(self, position: QPoint) -> None:  # noqa: C901
        if not position:  # From left-click on "Action" button
            position = self.viewport().mapFromGlobal(QCursor.pos())
            self.deselect_remote_folders()
            self.deselect_local_folders()
        cur_item = self.get_model().itemFromIndex(self.indexAt(position))
        if not cur_item:
            return
        cur_folder = self.get_model().item(cur_item.row(), 0).text()

        if self.gateway.magic_folder.folder_is_local(cur_folder):
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
        open_action = QAction(self.get_model().icon_folder_gray, "Open")
        open_action.triggered.connect(lambda: self.open_folders(selected))

        share_menu = QMenu()
        share_menu.setIcon(QIcon(resource("laptop.png")))
        share_menu.setTitle("Sync with device")  # XXX Rephrase?
        # invite_action = QAction(
        #    QIcon(resource("invite.png")), "Create Invite Code..."
        # )
        # invite_action.triggered.connect(
        #    lambda: self.open_invite_sender_dialog(selected)
        # )
        # share_menu.addAction(invite_action)

        if len(selected) == 1:  # XXX
            magic_folder_invite_action = QAction(
                QIcon(resource("invite.png")), "Create Invite Code..."
            )
            magic_folder_invite_action.triggered.connect(
                lambda: self.open_magic_folder_invite_dialog(selected[0])
            )
            share_menu.addAction(magic_folder_invite_action)

        remove_action = QAction(
            QIcon(resource("close.png")), "Remove from Recovery Key..."
        )
        menu.addAction(open_action)
        if features.magic_folder_invites:
            menu.addMenu(share_menu)
        menu.addSeparator()
        menu.addAction(remove_action)
        if selection_is_remote:
            open_action.setEnabled(False)
            share_menu.setEnabled(False)
            remove_action.triggered.connect(
                lambda: self.confirm_remove_folder_backup(selected)
            )
        else:
            for folder in selected:
                if not self.gateway.magic_folder.is_admin(folder):
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
    def add_folder(self, path: str) -> TwistedDeferred[None]:
        path = os.path.realpath(path)
        self.get_model().add_folder(path)
        folder_name = os.path.basename(path)
        try:
            yield Deferred.fromCoroutine(
                self.gateway.magic_folder.add_folder(path, "admin")
            )
        except Exception as e:  # pylint: disable=broad-except
            logging.error("%s: %s", type(e).__name__, str(e))
            try:
                reason = str(e.reason)  # type: ignore[attr-defined]
            except AttributeError:
                reason = f"{type(e).__name__}: {str(e)}"
            error(
                self,
                f'Error adding "{folder_name}" folder',
                f'An error occurred when adding the "{folder_name}" folder: '
                f"{reason}\n\nPlease try again later.",
                traceback(e),
            )
            self.get_model().remove_folder(folder_name)
            return
        logging.debug('Successfully added folder "%s"', folder_name)

    def add_folders(self, paths: list[str]) -> None:
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
            elif self.gateway.magic_folder.folder_exists(basename):
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
            self.gui.main_window.show_folders_view()  # XXX
            tasks = []
            for path in paths_to_add:
                tasks.append(self.add_folder(path))
            DeferredList(tasks)  # XXX

    def select_folder(self) -> None:
        dialog = QFileDialog(self, "Please select a folder")
        dialog.setDirectory(os.path.expanduser("~"))
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly)
        if dialog.exec_():
            self.add_folders(dialog.selectedFiles())

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        logging.debug(event)
        if event.mimeData().hasUrls():
            event.accept()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        logging.debug(event)
        event.accept()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasUrls():
            event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        logging.debug(event)
        if event.mimeData().hasUrls():
            event.accept()
            paths = []
            for url in event.mimeData().urls():
                paths.append(url.toLocalFile())
            self.add_folders(paths)

    def eventFilter(self, _: QObject, event: QEvent) -> bool:
        if isinstance(event, QDragEnterEvent):
            self.dragEnterEvent(event)
            return True
        if isinstance(event, QDragLeaveEvent):
            self.dragLeaveEvent(event)
            return True
        if isinstance(event, QDragMoveEvent):
            self.dragMoveEvent(event)
            return True
        if isinstance(event, QDropEvent):
            self.dropEvent(event)
            return True
        return False

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self.get_model().rowCount():
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

    def showEvent(self, _: QShowEvent) -> None:
        # Wrapping this in a timer makes it fire *after* all events in
        # the queue have been processed -- in this case, those needed
        # to actually render or show this view to the user; without it,
        # the prompt will be displayed -- and will block -- before the
        # other underlying UI elements are fully drawn (leading to the
        # appearance of a "blank" window beneath the dialog).
        QTimer.singleShot(0, self.maybe_prompt_for_recovery)


class Delegate(QStyledItemDelegate):
    def __init__(self, parent: View) -> None:
        super().__init__(parent)
        self._parent = parent

        self.waiting_movie = QMovie(resource("waiting.gif"))
        self.waiting_movie.setCacheMode(QMovie.CacheAll)
        self.waiting_movie.frameChanged.connect(self.on_frame_changed)
        self.sync_movie = QMovie(resource("sync.gif"))
        self.sync_movie.setCacheMode(QMovie.CacheAll)
        self.sync_movie.frameChanged.connect(self.on_frame_changed)

    def on_frame_changed(self) -> None:
        values = self._parent.get_model().status_dict.values()
        if (
            MagicFolderStatus.LOADING in values
            or MagicFolderStatus.WAITING in values
            or MagicFolderStatus.SYNCING in values
        ):
            self._parent.viewport().update()
        else:
            self.waiting_movie.setPaused(True)
            self.sync_movie.setPaused(True)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        column = index.column()
        if column == 1:
            pixmap = None
            status = index.data(Qt.UserRole)
            if status in (
                MagicFolderStatus.LOADING,
                MagicFolderStatus.WAITING,
            ):
                self.waiting_movie.setPaused(False)
                pixmap = self.waiting_movie.currentPixmap().scaled(
                    20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            elif status == MagicFolderStatus.SYNCING:
                self.sync_movie.setPaused(False)
                pixmap = self.sync_movie.currentPixmap().scaled(
                    20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            if pixmap:
                point = option.rect.topLeft()
                painter.drawPixmap(QPoint(point.x(), point.y() + 5), pixmap)
                option.rect = option.rect.translated(pixmap.width(), 0)
        super().paint(painter, option, index)
