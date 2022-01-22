#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'
__docformat__ = 'restructuredtext en'

import os, time, shutil, copy
# calibre Python 3 compatibility.
from six import text_type as unicode

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from collections import OrderedDict

try:
    from qt.core import (Qt, QToolButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
                            QFormLayout, QAction, QDialog, QTableWidget,
                            QTableWidgetItem, QAbstractItemView, QComboBox, QCheckBox,
                            QGroupBox, QGridLayout, QRadioButton, QDialogButtonBox,
                            QPushButton, QSpacerItem, QSizePolicy)
except ImportError:
    from PyQt5.Qt import (Qt, QToolButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
                            QFormLayout, QAction, QDialog, QTableWidget,
                            QTableWidgetItem, QAbstractItemView, QComboBox, QCheckBox,
                            QGroupBox, QGridLayout, QRadioButton, QDialogButtonBox,
                            QPushButton, QSpacerItem, QSizePolicy)

try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve

from functools import partial
from calibre.gui2 import error_dialog, question_dialog, info_dialog, warning_dialog
from calibre.gui2.ui import get_gui
from calibre.gui2.widgets2 import Dialog
from calibre.ebooks.metadata import string_to_authors
from calibre.library.field_metadata import FieldMetadata

from .common_utils import debug_print, PREFS_library, CustomColumns, equals_no_case, ImageTitleLayout, KeyValueComboBox, CustomColumnComboBox, KeyboardConfigDialog, get_icon
from .marc_relators import CONTRIBUTORS_ROLES, CONTRIBUTORS_DESCRIPTION

GUI = get_gui()

class ICON:
    PLUGIN    = 'images/plugin.png'
    WARNING   = 'images/warning.png'
    
    ALL = [
        PLUGIN,
        WARNING,
    ]


class KEY:
    OPTION_CHAR = '_'
    AUTO_IMPORT = OPTION_CHAR + 'autoImport'
    FIRST = OPTION_CHAR + 'firstLauch'
    FIRST_DEFAULT = True
    
    LINK_AUTHOR = OPTION_CHAR + 'linkAuthors'
    
    # ROLE<>AUTHOR
    ROLE = 'aut'
    AUTHOR = 'authors'
    
    AUTHOR_LOCAL = FieldMetadata()._tb_cats['authors']['name']
    AUTHOR_COLUMN = '{:s} ({:s})'.format(AUTHOR, AUTHOR_LOCAL)
    
    @staticmethod
    def exclude_option(contributors_pair_list):
        return {k:v for k, v in contributors_pair_list.items() if not k.startswith(KEY.OPTION_CHAR)}
    
    @staticmethod
    def exclude_invalide(contributors_pair_list):
        link = contributors_pair_list[KEY.LINK_AUTHOR]
        valide_columns = CustomColumns.get_names().keys()
        
        contributors_pair_list = KEY.exclude_option(contributors_pair_list)
        for k, v in copy.copy(contributors_pair_list).items():
            if not k or k not in CONTRIBUTORS_ROLES or not v or v not in valide_columns:
                contributors_pair_list.pop(k, None)
        
        if link:
            contributors_pair_list[KEY.ROLE] = KEY.AUTHOR
        return contributors_pair_list


PREFS = PREFS_library()
PREFS.defaults[KEY.AUTO_IMPORT] = False
PREFS.defaults[KEY.LINK_AUTHOR] = False
PREFS.defaults[KEY.FIRST] = KEY.FIRST_DEFAULT


class ConfigWidget(QWidget):
    def __init__(self, plugin_action):
        QWidget.__init__(self)
        
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        
        title_layout = ImageTitleLayout(self, ICON.PLUGIN, _('ePub Contributor Metatadata option'))
        layout.addLayout(title_layout)
        
        # Add a horizontal layout containing the table and the buttons next to it
        table_layout = QHBoxLayout()
        layout.addLayout(table_layout)
        
        # Create a table the user can edit the menu list
        self.table = ContributorColumnTableWidget(PREFS(), self)
        table_layout.addWidget(self.table)
        
        # Add a vertical layout containing the the buttons to move ad/del etc.
        button_layout = QVBoxLayout()
        table_layout.addLayout(button_layout)
        add_button = QToolButton(self)
        add_button.setToolTip(_('Add menu item'))
        add_button.setIcon(get_icon('plus.png'))
        button_layout.addWidget(add_button)
        button_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        delete_button = QToolButton(self)
        delete_button.setToolTip(_('Delete menu item'))
        delete_button.setIcon(get_icon('minus.png'))
        button_layout.addWidget(delete_button)
        button_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        add_button.clicked.connect(self.table.add_row)
        delete_button.clicked.connect(self.table.delete_rows)
        
        
        # --- Keyboard shortcuts ---
        keyboard_layout = QHBoxLayout()
        layout.addLayout(keyboard_layout)
        keyboard_shortcuts_button = QPushButton(_('Keyboard shortcuts...'), self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        keyboard_layout.addWidget(keyboard_shortcuts_button)
        keyboard_layout.insertStretch(-1)
        
        
        self.linkAuthors = QCheckBox(_('Embed "{:s}" column').format(KEY.AUTHOR_COLUMN), self)
        self.linkAuthors.setToolTip(_('Embed the "{:s}" column in the Contributors metadata. This a write-only option, the import action will not change the Calibre {:s} column.').format(KEY.AUTHOR_COLUMN, KEY.AUTHOR_LOCAL))
        self.linkAuthors.setChecked(PREFS[KEY.LINK_AUTHOR])
        keyboard_layout.addWidget(self.linkAuthors)
        
        self.autoImport = QCheckBox(_('Automatic import'), self)
        self.linkAuthors.setToolTip(_('Automatically import Contributors of new added books.'))
        self.autoImport.setChecked(PREFS[KEY.AUTO_IMPORT])
        keyboard_layout.addWidget(self.autoImport)
    
    def validate(self):
        valide = self.table.valide_contributors_columns()
        if not valide: warning_dialog(self, _('Duplicate values'),
                _('The current parameters contain duplicate values. Your changes have been cancelled.'),
                show=True, show_copy_button=False)
            
        return valide
    
    def save_settings(self):
        prefs = self.table.get_contributors_columns()
        prefs[KEY.LINK_AUTHOR] = self.linkAuthors.checkState() == Qt.Checked
        prefs[KEY.AUTO_IMPORT] = self.autoImport.checkState() == Qt.Checked
        prefs[KEY.FIRST] = False
        
        if prefs[KEY.LINK_AUTHOR]:
            poped = prefs.pop(KEY.ROLE, None)
            if poped:
                prefs[str(len(prefs)+1)] = poped
        
        PREFS(prefs)
        debug_print('Save settings:\n{0}\n'.format(PREFS))
    
    def edit_shortcuts(self):
        self.plugin_action.rebuild_menus()
        d = KeyboardConfigDialog(self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            GUI.keyboard.finalize()
    


class ContributorsEditDialog(Dialog):
    def __init__(self, contributors_list=None, book_ids=[]):
        self.contributors_list = contributors_list
        self.widget = ContributorsEditTableWidget(contributors_list)
        Dialog.__init__(self, _('_________________'), 'config_query_SearchReplace')
    
    def setup_ui(self):
        l = QVBoxLayout()
        self.setLayout(l)
        l.addWidget(self.widget)
        l.addWidget(self.bb)
    
    def accept(self):
        
        err = None
        
        if err:
            if question_dialog(self, _('Invalid operation'),
                             _('The registering of Find/Replace operation has failed.\n{:s}\nDo you want discard the changes?').format(str(err)),
                             default_yes=True, show_copy_button=False, override_icon=get_icon('dialog_warning.png')):
                
                Dialog.reject(self)
                return
            else:
                return
        
        self.operation = self.widget.save_settings()
        debug_print('Saved operation > {0}\n{1}\n'.format(operation_string(self.operation), self.operation))
        Dialog.accept(self)



COL_NAMES = [_('Contributor type'), _('Column')]
class ContributorColumnTableWidget(QTableWidget):
    def __init__(self, contributors_pair_list=None, *args):
        QTableWidget.__init__(self, *args)
        
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSortingEnabled(False)
        self.setMinimumSize(600, 0)
        
        self.populate_table(contributors_pair_list)
        
    
    def populate_table(self, contributors_pair_list=None):
        self.clear()
        self.setColumnCount(len(COL_NAMES))
        self.setHorizontalHeaderLabels(COL_NAMES)
        self.verticalHeader().setDefaultSectionSize(24)
        
        if contributors_pair_list == None: contributors_pair_list = {}
        first = contributors_pair_list.get(KEY.FIRST, KEY.FIRST_DEFAULT)
        contributors_pair_list = KEY.exclude_option(contributors_pair_list)
        
        
        
        if first and not contributors_pair_list:
            columns = CustomColumns.get_names()
            for role in CONTRIBUTORS_ROLES:
                for column in columns:
                    if equals_no_case('#'+role, column.name):
                        contributors_pair_list[role] = column.name
        
        
        self.setRowCount(len(contributors_pair_list))
        for row, contributors_pair in enumerate(contributors_pair_list.items(), 0):
            self.populate_table_row(row, contributors_pair)
        
        self.selectRow(0)
    
    def populate_table_row(self, row, contributors_pair):
        self.blockSignals(True)
        
        if contributors_pair == None: contributors_pair = ('','')
        self.setCellWidget(row, 0, ContributorsComboBox(self, 0, contributors_pair[0]))
        self.setCellWidget(row, 1, DuplicColumnComboBox(self, 1, contributors_pair[1]))
        
        self.resizeColumnsToContents()
        self.blockSignals(False)
    
    def add_row(self):
        self.setFocus()
        # We will insert a blank row below the currently selected row
        row = self.currentRow() + 1
        self.insertRow(row)
        self.populate_table_row(row, None)
        self.select_and_scroll_to_row(row)
    
    def delete_rows(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        message = _('Are you sure you want to delete this menu item?')
        if len(rows) > 1:
            message = _('Are you sure you want to delete the selected {:d} menu items?').format(len(rows))
        if not question_dialog(self, _('Are you sure?'), message, show_copy_button=False):
            return
        first_sel_row = self.currentRow()
        for selrow in reversed(rows):
            self.removeRow(selrow.row())
        if first_sel_row < self.rowCount():
            self.select_and_scroll_to_row(first_sel_row)
        elif self.rowCount() > 0:
            self.select_and_scroll_to_row(first_sel_row - 1)
    
    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())
    
    
    def valide_contributors_columns(self):
        key = [ self.cellWidget(row, 0).selected_key() for row in range(self.rowCount()) ]
        val = [ self.cellWidget(row, 1).selected_column() for row in range(self.rowCount()) ]
        
        dk = duplicate_entry(key)
        if '' in dk: dk.remove('')
        bk = bool(dk)
        dv = duplicate_entry(val)
        if '' in dv: dv.remove('')
        bv = bool(dv)
        
        return not(bv or bv)
    
    def get_contributors_columns(self):
        contributors_columns = {}
        for row in range(self.rowCount()):
            k = self.cellWidget(row, 0).selected_key()
            v = self.cellWidget(row, 1).selected_column()
            
            if k or v:
                contributors_columns[k if k else str(row)] = v if v else ''
        
        return contributors_columns


COL_CONTRIBUTORS = [_('Contributor type'), _('Names')]
class ContributorsEditTableWidget(QTableWidget):
    def __init__(self, contributors_list=None, *args):
        QTableWidget.__init__(self, *args)
        
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSortingEnabled(False)
        self.setMinimumSize(600, 0)
        
        self.populate_table(contributors_list)
        
    
    def populate_table(self, contributors_list=None):
        self.clear()
        self.setColumnCount(len(COL_CONTRIBUTORS))
        self.setHorizontalHeaderLabels(COL_CONTRIBUTORS)
        self.verticalHeader().setDefaultSectionSize(24)
        
        if contributors_list == None: contributors_list = {}
        self.setRowCount(len(contributors_list))
        for row, contributors in enumerate(contributors_list, 0):
            self.populate_table_row(row, contributors)
        
        self.selectRow(0)
    
    def populate_table_row(self, row, contributors):
        self.blockSignals(True)
        
        if contributors == None: contributors = ('','')
        self.setCellWidget(row, 0, ContributorsComboBox(self, 0, contributors[0]))
        self.setCellWidget(row, 1, QTableWidgetItem(' & '.joint(contributors[1])))
        
        self.resizeColumnsToContents()
        self.blockSignals(False)
    
    def add_row(self):
        self.setFocus()
        # We will insert a blank row below the currently selected row
        row = self.currentRow() + 1
        self.insertRow(row)
        self.populate_table_row(row, None)
        self.select_and_scroll_to_row(row)
    
    def delete_rows(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        message = _('Are you sure you want to delete this menu item?')
        if len(rows) > 1:
            message = _('Are you sure you want to delete the selected {:d} menu items?').format(len(rows))
        if not question_dialog(self, _('Are you sure?'), message, show_copy_button=False):
            return
        first_sel_row = self.currentRow()
        for selrow in reversed(rows):
            self.removeRow(selrow.row())
        if first_sel_row < self.rowCount():
            self.select_and_scroll_to_row(first_sel_row)
        elif self.rowCount() > 0:
            self.select_and_scroll_to_row(first_sel_row - 1)
    
    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())
    
    def get_contributors_names(self):
        contributors_columns = {}
        for row in range(self.rowCount()):
            k = self.cellWidget(row, 0).selected_key()
            
            if k:
                contributors_columns[k] = string_to_authors(self.cellWidget(row, 1))
        
        return contributors_columns


class ContributorsComboBox(KeyValueComboBox):
    def __init__(self, table, column, selected_contributors):
        KeyValueComboBox.__init__(self, table, CONTRIBUTORS_ROLES, selected_contributors, values_ToolTip=CONTRIBUTORS_DESCRIPTION)
        self.table = table
        self.column = column
        self.currentIndexChanged.connect(self.test_contributors_changed)
    
    def wheelEvent(self, event):
        # Disable the mouse wheel on top of the combo box changing selection as plays havoc in a grid
        event.ignore()
    
    def test_contributors_changed(self, val):
        de = duplicate_entry([self.table.cellWidget(row, self.column).currentText() for row in range(self.table.rowCount())])
        if de.count(''): de.remove('')
        if de and de.count(self.currentText()):
            warning_dialog(self, _('Duplicate Contributors type'),
                _('A Contributor was duplicated!\nChange the settings so that each contributor is present only once, otherwise the settings can not be saved.\n\nDuplicate type:')
                + '\n' + '\n'.join(de),
                show=True, show_copy_button=False)


class DuplicColumnComboBox(CustomColumnComboBox):
    def __init__(self, table, column, selected_column):
        CustomColumnComboBox.__init__(self, table, CustomColumns.get_names(), selected_column, initial_items=[''])
        self.table = table
        self.column = column
        self.currentIndexChanged.connect(self.test_column_changed)
    
    def wheelEvent(self, event):
        # Disable the mouse wheel on top of the combo box changing selection as plays havoc in a grid
        event.ignore()
    
    def test_column_changed(self, val):
        de = duplicate_entry([self.table.cellWidget(row, self.column).currentText() for row in range(self.table.rowCount())])
        if de.count(''): de.remove('')
        if de and de.count(self.currentText()):
            warning_dialog(self, _('Duplicate Custom column'),
                _('A Custom column was duplicated!\nChange the settings so that each Custom column is present only once, otherwise the settings can not be saved.\n\nDuplicate column:')
                + '\n' + '\n'.join(de),
                show=True, show_copy_button=False)


def duplicate_entry(lst):
    return list( set([x for x in lst if lst.count(x) > 1]) )
