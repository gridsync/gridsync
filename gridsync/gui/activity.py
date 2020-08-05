# -*- coding: utf-8 -*-

from datetime import datetime
import os
import time

from humanize import naturalsize, naturaltime
from PyQt5.QtCore import (
    QFileInfo,
    QModelIndex,
    QSize,
    QSortFilterProxyModel,
    QTimer,
    Qt,
)
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtGui import (
    QCursor,
    QIcon,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PyQt5.QtWidgets import (
    QAction,
    QAbstractItemView,
    QFileIconProvider,
    QGridLayout,
    QLabel,
    QListView,
    QListWidgetItem,
    QListWidget,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStyledItemDelegate,
    QTableView,
    QToolButton,
    QWidget,
)

from gridsync import resource
from gridsync.desktop import open_enclosing_folder, open_path
from gridsync.gui.color import BlendedColor
from gridsync.gui.font import Font


DATA_ROLE = Qt.UserRole
LOCATION_ROLE = Qt.UserRole + 1
MTIME_ROLE = Qt.UserRole + 2


class ActivityItemWidget(QWidget):
    def __init__(self, gateway, folder_name, data, parent):
        super().__init__()
        self.gateway = gateway
        self.data = data
        self.parent = parent

        self.path = data["path"]
        self.size = data["size"]
        self.action = data["action"]
        self.mtime = data["mtime"]
        self._thumbnail_loaded = False

        dirname, self.basename = os.path.split(self.path)
        if dirname:
            self.location = f"{self.gateway.name}/{folder_name}/{dirname}"
        else:
            self.location = f"{self.gateway.name}/{folder_name}"

        self.local_path = os.path.join(
            self.gateway.get_magic_folder_directory(folder_name), self.path
        )

        self.setAutoFillBackground(True)
        self.setToolTip(
            "{}\n\nSize: {}\nModified: {}".format(
                self.local_path, naturalsize(self.size), time.ctime(self.mtime)
            )
        )

        self.icon = QLabel()
        self.icon.setPixmap(
            QFileIconProvider().icon(QFileInfo(self.local_path)).pixmap(48, 48)
        )

        self.basename_label = QLabel(self.basename)
        self.basename_label.setFont(Font(11))

        self.details_label = QLabel()
        self.details_label.setFont(Font(10))
        palette = self.palette()
        dimmer_grey = BlendedColor(
            palette.text().color(), palette.base().color(), 0.6
        ).name()
        self.details_label.setStyleSheet("color: {}".format(dimmer_grey))

        self.button = QPushButton()
        self.button.setIcon(QIcon(resource("dots-horizontal-triple.png")))
        self.button.setStyleSheet("border: none;")
        self.button.clicked.connect(self.parent.on_right_click)
        self.button.hide()

        self.layout = QGridLayout(self)
        self.layout.addWidget(self.icon, 1, 1, 2, 2)
        self.layout.addWidget(self.basename_label, 1, 3)
        self.layout.addWidget(self.details_label, 2, 3)
        self.layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 4, 4)
        self.layout.addWidget(self.button, 1, 5, 2, 2)

        self.update_text()
        QTimer.singleShot(50, self.load_thumbnail)

    def update_text(self):
        self.details_label.setText(
            "{} {}".format(
                self.action.capitalize(),
                naturaltime(datetime.fromtimestamp(self.mtime)),
            )
        )

    def _do_load_thumbnail(self):
        pixmap = QPixmap(self.local_path)
        if not pixmap.isNull():
            self.icon.setPixmap(
                pixmap.scaled(
                    48, 48, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
                )
            )

    def load_thumbnail(self):
        if self.isVisible() and not self._thumbnail_loaded:
            self._thumbnail_loaded = True
            QTimer.singleShot(50, self._do_load_thumbnail)

    def unhighlight(self):
        self.button.hide()
        palette = self.palette()
        palette.setColor(self.backgroundRole(), self.parent.base_color)
        self.setPalette(palette)

    def enterEvent(self, _):
        self.button.show()
        palette = self.palette()
        palette.setColor(self.backgroundRole(), self.parent.highlighted_color)
        self.setPalette(palette)
        if self.parent.highlighted and self.parent.highlighted is not self:
            try:
                self.parent.highlighted.unhighlight()
            except RuntimeError:  # Object has been deleted
                pass
        self.parent.highlighted = self


class ActivityItemMenu(QMenu):
    def __init__(self, item, parent):
        super().__init__(parent)
        print(item)
        widget = parent.itemWidget(item)

        open_file_action = QAction("Open file", self)
        open_file_action.triggered.connect(
            lambda: open_path(widget.local_path)
        )
        open_folder_action = QAction("Open enclosing folder", self)
        open_folder_action.triggered.connect(
            lambda: open_enclosing_folder(widget.local_path)
        )

        self.addAction(open_file_action)
        self.addAction(open_folder_action)


# class ActivityListWidget(QListWidget):
class ActivityView(QListWidget):
    def __init__(self, gateway, deduplicate=True, max_items=30):
        super().__init__()
        self.gateway = gateway
        self.deduplicate = deduplicate
        self.max_items = max_items

        palette = self.palette()
        self.base_color = palette.base().color()
        self.highlighted_color = BlendedColor(
            self.base_color, palette.highlight().color(), 0.88
        )  # Was #E6F1F7
        self.highlighted = None

        self.action_icon = QIcon(resource("dots-horizontal-triple.png"))

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setFocusPolicy(Qt.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        # self.setStyleSheet("QListWidget::item:hover { background: #E6F1F7 }")
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.sb = self.verticalScrollBar()

        self.sb.valueChanged.connect(self.update_visible_widgets)
        self.itemDoubleClicked.connect(self.on_double_click)
        self.customContextMenuRequested.connect(self.on_right_click)

        self.gateway.monitor.file_updated.connect(self.add_item)
        self.gateway.monitor.check_finished.connect(
            self.update_visible_widgets
        )

    def on_double_click(self, item):
        open_enclosing_folder(self.itemWidget(item).path)

    def on_right_click(self, position):
        if not position:
            position = self.viewport().mapFromGlobal(QCursor().pos())
        item = self.itemAt(position)
        if not item:
            return
        menu = ActivityItemMenu(item, self)
        menu.exec_(self.viewport().mapToGlobal(position))

    def add_item(self, folder_name, data):
        path = data.get("path")
        if path.endswith(os.path.sep):
            return
        duplicate = None
        if self.deduplicate:
            for i in range(self.count()):
                widget = self.itemWidget(self.item(i))
                if (
                    widget
                    and widget.data["path"] == path
                    and widget.data["member"] == data["member"]
                ):
                    duplicate = i
                    break
        if duplicate is not None:
            item = self.takeItem(duplicate)
        else:
            self.takeItem(self.max_items)
            item = QListWidgetItem()
        self.insertItem(0 - int(data["mtime"]), item)  # Newest on top
        custom_widget = ActivityItemWidget(
            self.gateway, folder_name, data, self
        )
        item.setSizeHint(custom_widget.sizeHint())
        self.setItemWidget(item, custom_widget)

    def filter_by_location(self, location: str) -> None:
        for i in range(self.count()):
            item = self.item(i)
            if self.itemWidget(item).location.startswith(location):
                item.setHidden(False)
            else:
                item.setHidden(True)

    def filter_by_remote_paths(self, remote_paths: list) -> None:  # XXX
        items_to_show = []
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            widget_remote_path = os.path.join(widget.location, widget.basename)
            for path in remote_paths:
                if widget_remote_path.startswith(path):
                    items_to_show.append(item)
        for i in range(self.count()):
            item = self.item(i)
            if item in items_to_show:
                item.setHidden(False)
            else:
                item.setHidden(True)

    def update_visible_widgets(self):
        if not self.isVisible():
            return
        rect = self.viewport().contentsRect()
        top = self.indexAt(rect.topLeft())
        if top.isValid():
            bottom = self.indexAt(rect.bottomLeft())
            if not bottom.isValid():
                bottom = self.model().index(self.count() - 1)
            for index in range(top.row(), bottom.row() + 1):
                widget = self.itemWidget(self.item(index))
                if widget:
                    widget.update_text()
                    widget.load_thumbnail()

    def showEvent(self, _):
        self.update_visible_widgets()


class ActivityWidget(QWidget):
    def __init__(self, index, view, parent):
        super().__init__(parent)
        self.index = index
        self.view = view

        self.item = self.view.source_item(index)

        self.icon = QLabel()
        self.icon.setPixmap(
            QFileIconProvider().icon(QFileInfo("/home/user/1")).pixmap(48, 48)
        )

        self.basename_label = QLabel(self.item.text())
        self.basename_label.setFont(Font(11))

        self.details_label = QLabel("details")
        self.details_label.setFont(Font(10))

        self._palette = self.palette()
        dimmer_grey = BlendedColor(
            self._palette.text().color(), self._palette.base().color(), 0.6
        ).name()
        self.details_label.setStyleSheet(f"color: {dimmer_grey}")

        self.button = QPushButton()
        self.button.setIcon(QIcon(resource("dots-horizontal-triple.png")))
        self.button.setStyleSheet("border: none;")
        # self.button.clicked.connect(self.parent.on_right_click)
        # self.button.hide()

        self.setAutoFillBackground(True)

        layout = QGridLayout(self)
        layout.addWidget(self.icon, 1, 1, 2, 2)
        layout.addWidget(self.basename_label, 1, 3)
        layout.addWidget(self.details_label, 2, 3)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 4, 4)
        layout.addWidget(self.button, 1, 5, 2, 2)

        self.leaveEvent(None)

    def enterEvent(self, _):
        self._palette.setColor(
            self.backgroundRole(), self.view.highlight_color
        )
        self.setPalette(self._palette)
        self.button.show()
        print(self.item.text())

    def leaveEvent(self, _):
        self._palette.setColor(self.backgroundRole(), self.view.base_color)
        self.setPalette(self._palette)
        self.button.hide()


class ActivityDelegate(QStyledItemDelegate):

    button_clicked = Signal(QModelIndex)

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self._button_icon = QIcon(resource("dots-horizontal-triple.png"))

    def createEditor(
        self, parent, option, index
    ):  # pylint: disable=unused-argument
        widget = ActivityWidget(index, self.view, parent)
        widget.button.clicked.connect(lambda: self.button_clicked.emit(index))
        return widget

    def paint(self, painter, option, index):  # pylint: disable=unused-argument
        self.view.openPersistentEditor(index)


class ActivityModel(QStandardItemModel):

    item_added = Signal(QStandardItem)

    def __init__(self, gateway, parent=None):
        super().__init__(parent)
        self.gateway = gateway
        self.gateway.monitor.file_updated.connect(self.on_file_updated)
        # self.parent = parent

    def add_item(self, folder_name, data):
        dirname, basename = os.path.split(data.get("path", ""))
        if dirname:
            location = f"{self.gateway.name}/{folder_name}/{dirname}"
        else:
            location = f"{self.gateway.name}/{folder_name}"

        item = QStandardItem(basename)
        item.setData(data, DATA_ROLE)
        item.setData(location, LOCATION_ROLE)
        item.setData(str(data.get("mtime", 0)), MTIME_ROLE)
        # self.insertRow(0, [item])
        self.appendRow([item])
        self.item_added.emit(item)
        # w = ActivityWidget(item.index(), self.parent, self)
        # w = QLabel('test')
        # self.parent.setIndexWidget(item.index(), w)

    def on_file_updated(self, folder_name, data):
        self.add_item(folder_name, data)


# class ActivityView(QListView):
class ActivityView_(QTableView):
    def __init__(self, gateway, parent=None):
        super().__init__(parent)
        self.gateway = gateway

        _palette = self.palette()
        self.base_color = _palette.base().color()
        self.highlight_color = BlendedColor(
            self.base_color, _palette.highlight().color(), 0.88
        )  # Was #E6F1F7

        self.setShowGrid(False)

        horizontal_header = self.horizontalHeader()
        horizontal_header.setStretchLastSection(True)
        horizontal_header.hide()

        vertical_header = self.verticalHeader()
        vertical_header.setDefaultSectionSize(64)
        vertical_header.hide()

        self.source_model = ActivityModel(gateway, self)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterKeyColumn(0)
        self.proxy_model.setFilterRole(LOCATION_ROLE)
        self.proxy_model.setSortRole(MTIME_ROLE)
        self.proxy_model.sort(0, Qt.DescendingOrder)  # Latest changes on top

        self.setModel(self.proxy_model)

        # self.proxy_model.setFilterRegularExpression("t")

        self.setItemDelegate(ActivityDelegate(self))

    def source_item(self, proxy_model_index: QModelIndex) -> QStandardItem:
        source_index = self.proxy_model.mapToSource(proxy_model_index)
        return self.source_model.itemFromIndex(source_index)

    def filter_by_location(self):
        pass

    def filter_by_remote_paths(self):
        pass
