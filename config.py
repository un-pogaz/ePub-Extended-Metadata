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
    QPolicy = QSizePolicy.Policy
except:
    QPolicy = QSizePolicy

try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve

from functools import partial
from calibre.gui2 import error_dialog, question_dialog, info_dialog, warning_dialog
from calibre.gui2.widgets2 import Dialog
from calibre.ebooks.metadata import string_to_authors

from calibre_plugins.edit_contributors_metadata.common_utils import (ImageTitleLayout, KeyValueComboBox, CustomColumnComboBox, KeyboardConfigDialog,
                                                              get_icon, get_library_uuid, debug_print)
                                                              
from calibre_plugins.edit_contributors_metadata.marc_relators import CONTRIBUTORS_ROLES, CONTRIBUTORS_DERCRIPTION


class ICON:
    PLUGIN    = 'images/plugin.png'
    WARNING   = 'images/warning.png'
    
    ALL = [
        PLUGIN,
        WARNING,
    ]

class KEY:
    CONTRIBUTOR = 'role'
    COLUMN = 'column'
    NAMES = 'names'
    OPTION_CHAR = '_'
    AUTO_IMPORT = OPTION_CHAR + 'auto_import'



PREFS_NAMESPACE = 'EditContributors'
PREFS_KEY_SETTINGS = 'settings'
PREFS_DEFAULT = { KEY.AUTO_IMPORT : False }

def get_library_config(db):
    library_id = get_library_uuid(db)
    library_config = None

    if library_config is None:
        library_config = db.prefs.get_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS, PREFS_DEFAULT)
    return library_config

def set_library_config(db, library_config):
    db.prefs.set_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS, library_config)


class ConfigWidget(QWidget):
    def __init__(self, plugin_action):
        QWidget.__init__(self)
        
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        
        title_layout = ImageTitleLayout(self, ICON.PLUGIN, _('Edit Contributor Metatadata option'))
        layout.addLayout(title_layout)
        
        PREFS = get_library_config(self.plugin_action.gui.current_db)
        
        # Add a horizontal layout containing the table and the buttons next to it
        table_layout = QHBoxLayout()
        layout.addLayout(table_layout)
        
        # Create a table the user can edit the menu list
        self.table = ContributorColumnTableWidget(plugin_action, PREFS, self)
        table_layout.addWidget(self.table)
        
        # Add a vertical layout containing the the buttons to move ad/del etc.
        button_layout = QVBoxLayout()
        table_layout.addLayout(button_layout)
        add_button = QToolButton(self)
        add_button.setToolTip(_('Add menu item'))
        add_button.setIcon(get_icon('plus.png'))
        button_layout.addWidget(add_button)
        button_layout.addItem(QSpacerItem(20, 40, QPolicy.Minimum, QPolicy.Expanding))
        
        delete_button = QToolButton(self)
        delete_button.setToolTip(_('Delete menu item'))
        delete_button.setIcon(get_icon('minus.png'))
        button_layout.addWidget(delete_button)
        button_layout.addItem(QSpacerItem(20, 40, QPolicy.Minimum, QPolicy.Expanding))
        
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
        
        
        self.updateReport = QCheckBox(_('Auto import '), self)
        if PREFS[KEY.AUTO_IMPORT]:
            self.updateReport.setCheckState(Qt.Checked)
        else:
            self.updateReport.setCheckState(Qt.Unchecked)
        
        keyboard_layout.addWidget(self.updateReport)
    
    def validate(self):
        return True
    
    def save_settings(self):
        
        PREFS = self.table.get_contributors_columns()
        PREFS[KEY.AUTO_IMPORT] = self.updateReport.checkState() == Qt.Checked
        
        set_library_config(self.plugin_action.gui.current_db, PREFS)
        debug_print('Save settings:\n{0}\n'.format(PREFS))
    
    
    def edit_shortcuts(self):
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()
    


class ContributorsEditDialog(Dialog):
    def __init__(self, parent, plugin_action, contributors_list=None, book_ids=[]):
        self.plugin_action = plugin_action
        self.parent = parent
        self.contributors_list = contributors_list
        self.widget = ContributorsEditTableWidget(plugin_action, contributors_list)
        Dialog.__init__(self, _('Configuration of a Search/Replace operation'), 'config_query_SearchReplace', parent)
    
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
    def __init__(self, plugin_action, contributors_pair_list=None, *args):
        QTableWidget.__init__(self, *args)
        self.plugin_action = plugin_action
        self.gui = plugin_action.gui
        
        
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
        
        if contributors_pair_list == None: contributors_pair_list = []
        contributors_pair_list = {k:v for k, v in contributors_pair_list.items() if k[0] != KEY.OPTION_CHAR }
        self.setRowCount(len(contributors_pair_list))
        for row, contributors_pair in enumerate(contributors_pair_list.items(), 0):
            self.populate_table_row(row, contributors_pair)
        
        self.selectRow(0)
    
    def populate_table_row(self, row, contributors_pair):
        self.blockSignals(True)
        
        if contributors_pair == None: contributors_pair = ('','')
        self.setCellWidget(row, 0, ContributorsComboBox(self, contributors_pair[0]))
        self.setCellWidget(row, 1, CustomColumnComboBox(self, self.get_custom_columns(), contributors_pair[1]))
        
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
    
    def get_custom_columns(self):
        '''
        Gets matching custom columns for column_type
        '''
        custom_columns = self.gui.library_view.model().custom_columns
        available_columns = {}
        for key, column in custom_columns.items():
            if (column["datatype"] == "text" and bool(column["is_multiple"]) == True
              and column['display'].get('is_names', False) == True):
                available_columns[key] = column
        return available_columns
    
    def get_contributors_columns(self):
        contributors_columns = {}
        for row in range(self.rowCount()):
            k = self.cellWidget(row, 0).selected_key()
            v = self.cellWidget(row, 1).get_selected_column()
            
            if k or v:
                contributors_columns[k if k != None else str(row) ] = v if v != None else ''
        
        return contributors_columns

COL_CONTRIBUTORS = [_('Contributor type'), _('Names')]
class ContributorsEditTableWidget(QTableWidget):
    def __init__(self, plugin_action, contributors_list=None, *args):
        QTableWidget.__init__(self, *args)
        self.plugin_action = plugin_action
        self.gui = plugin_action.gui
        
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
        
        if contributors_list == None: contributors_list = []
        self.setRowCount(len(contributors_list))
        for row, contributors in enumerate(contributors_list, 0):
            self.populate_table_row(row, contributors)
        
        self.selectRow(0)
    
    def populate_table_row(self, row, contributors):
        self.blockSignals(True)
        
        if contributors == None: contributors = ('','')
        self.setCellWidget(row, 0, ContributorsComboBox(self, contributors[0]))
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
    def __init__(self, table, selected_contributors):
        KeyValueComboBox.__init__(self, table, CONTRIBUTORS_ROLES, selected_contributors)
        self.table = table
        self.currentIndexChanged.connect(self.test_contributors_changed)
    
    def test_contributors_changed(self, val):
        de = duplicate_entry([self.table.cellWidget(row, 0).currentText() for row in range(self.table.rowCount())])
        if de.count(''): de.remove('')
        if de and de.count(self.currentText()):
            warning_dialog(self, _('Duplicate Contributors type'),
                _('A Contributor was duplicated! Change the settings so that each contributor is present only once, otherwise the settings can not be saved.\nDuplicate type:')
                + '\n' + '\n'.join(de),
                show=True, show_copy_button=False)
    


def duplicate_entry(lst):
    return list( set([x for x in lst if lst.count(x) > 1]) )