# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'designer/newfolder.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(505, 224)
        self.verticalLayout_4 = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout_4.setObjectName(_fromUtf8("verticalLayout_4"))
        self.layout = QtGui.QVBoxLayout()
        self.layout.setObjectName(_fromUtf8("layout"))
        self.select_grid_group_box = QtGui.QGroupBox(Dialog)
        self.select_grid_group_box.setObjectName(_fromUtf8("select_grid_group_box"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.select_grid_group_box)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.select_grid_combo_box = QtGui.QComboBox(self.select_grid_group_box)
        self.select_grid_combo_box.setObjectName(_fromUtf8("select_grid_combo_box"))
        self.select_grid_combo_box.addItem(_fromUtf8(""))
        self.select_grid_combo_box.addItem(_fromUtf8(""))
        self.horizontalLayout.addWidget(self.select_grid_combo_box)
        self.layout.addWidget(self.select_grid_group_box)
        self.select_folder_group_box = QtGui.QGroupBox(Dialog)
        self.select_folder_group_box.setObjectName(_fromUtf8("select_folder_group_box"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.select_folder_group_box)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.select_folder_text = QtGui.QLineEdit(self.select_folder_group_box)
        self.select_folder_text.setObjectName(_fromUtf8("select_folder_text"))
        self.horizontalLayout_2.addWidget(self.select_folder_text)
        self.select_folder_button = QtGui.QPushButton(self.select_folder_group_box)
        self.select_folder_button.setObjectName(_fromUtf8("select_folder_button"))
        self.horizontalLayout_2.addWidget(self.select_folder_button)
        self.layout.addWidget(self.select_folder_group_box)
        self.verticalLayout_4.addLayout(self.layout)
        self.button_box = QtGui.QDialogButtonBox(Dialog)
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.button_box.setObjectName(_fromUtf8("button_box"))
        self.verticalLayout_4.addWidget(self.button_box)

        self.retranslateUi(Dialog)
        QtCore.QObject.connect(self.button_box, QtCore.SIGNAL(_fromUtf8("accepted()")), Dialog.accept)
        QtCore.QObject.connect(self.button_box, QtCore.SIGNAL(_fromUtf8("rejected()")), Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("Dialog", "Dialog", None))
        self.select_grid_group_box.setTitle(_translate("Dialog", "Select storage grid to use:", None))
        self.select_grid_combo_box.setItemText(0, _translate("Dialog", "test.gridsync.io", None))
        self.select_grid_combo_box.setItemText(1, _translate("Dialog", "Public Test Grid", None))
        self.select_folder_group_box.setTitle(_translate("Dialog", "Select folder to sync:", None))
        self.select_folder_button.setText(_translate("Dialog", "Browse...", None))

