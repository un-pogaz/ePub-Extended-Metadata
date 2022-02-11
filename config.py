#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'
__docformat__ = 'restructuredtext en'

import copy, time, os, shutil
# python3 compatibility
from six.moves import range
from six import text_type as unicode

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from datetime import datetime
from collections import defaultdict, OrderedDict
from functools import partial
from polyglot.builtins import iteritems, itervalues

try:
    from qt.core import (Qt, QToolButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
                            QFormLayout, QAction, QDialog, QTableWidget, QScrollArea,
                            QTableWidgetItem, QAbstractItemView, QComboBox, QCheckBox,
                            QGroupBox, QGridLayout, QRadioButton, QDialogButtonBox,
                            QPushButton, QSpacerItem, QSizePolicy, QTabWidget)
except ImportError:
    from PyQt5.Qt import (Qt, QToolButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
                            QFormLayout, QAction, QDialog, QTableWidget, QScrollArea,
                            QTableWidgetItem, QAbstractItemView, QComboBox, QCheckBox,
                            QGroupBox, QGridLayout, QRadioButton, QDialogButtonBox,
                            QPushButton, QSpacerItem, QSizePolicy, QTabWidget)

from calibre import prints
from calibre.gui2 import error_dialog, question_dialog, info_dialog, warning_dialog
from calibre.gui2.ui import get_gui
from calibre.gui2.widgets2 import Dialog
from calibre.ebooks.metadata import string_to_authors
from calibre.library.field_metadata import FieldMetadata
from polyglot.builtins import iteritems, itervalues

from .common_utils import (debug_print, get_icon, PREFS_library, PREFS_dynamic, KeyboardConfigDialog, ImageTitleLayout,
                            equals_no_case, duplicate_entry, get__init__attribut, KeyValueComboBox, CustomColumnComboBox, ReadOnlyTableWidgetItem)


from .marc_relators import CONTRIBUTORS_ROLES, CONTRIBUTORS_DESCRIPTION

GUI = get_gui()


class ICON:
    PLUGIN    = 'images/plugin.png'
    WARNING   = 'images/warning.png'
    
    ALL = [
        PLUGIN,
        WARNING,
    ]


class FIELD:
    '''
    contains the information to associate the data to a field 
    '''
    class AUTHOR:
        ROLE = 'aut'
        NAME = 'authors'
        LOCAL = FieldMetadata()._tb_cats['authors']['name']
        COLUMN = '{:s} ({:s})'.format(NAME, LOCAL)

class KEY:
    OPTION_CHAR = '_'
    AUTO_IMPORT = OPTION_CHAR + 'autoImport'
    AUTO_EMBED = OPTION_CHAR + 'autoEmbed'
    FIRST_CONFIG = OPTION_CHAR + 'firstConfig'
    LINK_AUTHOR = OPTION_CHAR + 'linkAuthors'
    CREATORS_AS_AUTHOR = OPTION_CHAR + 'creatorAsAuthors'
    
    KEEP_CALIBRE_MANUAL = OPTION_CHAR + 'keepCalibre_Manual'
    KEEP_CALIBRE_AUTO = OPTION_CHAR + 'keepCalibre_Auto'
    
    SHARED_COLUMNS = OPTION_CHAR + 'sharedColumns'
    
    CREATORS = 'creators'
    CONTRIBUTORS = 'contributors'
    
    # legacy ePub2
    COVERAGES = 'coverages'
    RELATIONS = 'relations'
    RIGHTS = 'rights'
    SOURCES = 'sources'
    TYPES = 'types'
    
    # ePub3
    SERIES = 'series'
    COLLECTIONS = 'collections'
    
    
    @staticmethod
    def find_plugin(key):
        from .common import NAME
        from calibre.customize.ui import find_plugin
        return find_plugin(NAME.WRITER if key == KEY.AUTO_EMBED else NAME.READER) 
    
    @staticmethod
    def enable_plugin(key):
        from calibre.customize.ui import enable_plugin
        p = KEY.find_plugin(key)
        if p: enable_plugin(p.name)
    
    @staticmethod
    def disable_plugin(key):
        from calibre.customize.ui import disable_plugin
        p = KEY.find_plugin(key)
        if p: disable_plugin(p.name)
    
    
    @staticmethod
    def get_current_columns():
        from .columns_metadata import get_columns_from_dict
        d = DYNAMIC[KEY.SHARED_COLUMNS]
        d = get_columns_from_dict(DYNAMIC[KEY.SHARED_COLUMNS])
        
        return get_columns_from_dict(DYNAMIC[KEY.SHARED_COLUMNS])
    
    @staticmethod
    def get_current_prefs():
        from .columns_metadata import get_columns_from_dict
        prefs = DYNAMIC.deepcopy_dict()
        current_columns = KEY.get_current_columns().keys()
        link = DYNAMIC[KEY.LINK_AUTHOR]
        
        prefs = {k:v for k, v in iteritems(prefs) if not k.startswith(KEY.OPTION_CHAR)}
        
        if KEY.CONTRIBUTORS not in prefs or not prefs[KEY.CONTRIBUTORS]:
            prefs[KEY.CONTRIBUTORS] = {}
        
        for k,v in iteritems(copy.copy(prefs)):
            if k == KEY.CONTRIBUTORS:
                for k,v in iteritems(copy.copy(prefs[KEY.CONTRIBUTORS])):
                    if not k or k not in CONTRIBUTORS_ROLES or not v or v not in current_columns:
                        prefs[KEY.CONTRIBUTORS].pop(k, None)
            elif not v or v not in current_columns:
                prefs.pop(k, None)
        
        if link:
            prefs[KEY.CONTRIBUTORS][FIELD.AUTHOR.ROLE] = FIELD.AUTHOR.NAME
        return prefs
    
    
    @staticmethod
    def get_names():
        from .columns_metadata import get_names
        return get_names(True)
    
    @staticmethod
    def get_used_columns():
        from .columns_metadata import get_columns_where, get_columns_from_dict
        treated_column = [v for k,v in iteritems(PREFS) if not k.startswith(KEY.OPTION_CHAR) and isinstance(v, unicode)] + [c for c in itervalues(PREFS[KEY.CONTRIBUTORS]) if isinstance(c, unicode)]
        def predicate(column):
            return column.is_custom and column.name in treated_column
        
        return {v.name:v.metadata for v in itervalues(get_columns_where(predicate=predicate))}


PREFS = PREFS_library()
PREFS.defaults[KEY.AUTO_IMPORT] = False
PREFS.defaults[KEY.AUTO_EMBED] = False
PREFS.defaults[KEY.LINK_AUTHOR] = False
PREFS.defaults[KEY.CREATORS_AS_AUTHOR] = False
PREFS.defaults[KEY.CONTRIBUTORS] = {}
PREFS.defaults[KEY.FIRST_CONFIG] = True
PREFS.defaults[KEY.KEEP_CALIBRE_MANUAL] = False
PREFS.defaults[KEY.KEEP_CALIBRE_AUTO] = True

DYNAMIC = PREFS_dynamic()
DYNAMIC.defaults = copy.deepcopy(PREFS.defaults)
DYNAMIC.defaults[KEY.SHARED_COLUMNS] = {}

def plugin_check_enable_library():
    if PREFS[KEY.AUTO_IMPORT]:
        KEY.enable_plugin(KEY.AUTO_IMPORT)
    else:
        KEY.disable_plugin(KEY.AUTO_IMPORT)
    
    if PREFS[KEY.AUTO_EMBED]:
        KEY.enable_plugin(KEY.AUTO_EMBED)
    else:
        KEY.disable_plugin(KEY.AUTO_EMBED)
    
    with DYNAMIC:
        DYNAMIC.update(PREFS.deepcopy_dict())
        DYNAMIC[KEY.SHARED_COLUMNS] = KEY.get_used_columns()

def plugin_realy_enable(key):
    from calibre.customize.ui import is_disabled
    p = KEY.find_plugin(key)
    if p:
        enable = not is_disabled(p)
        if PREFS[key] != enable:
            PREFS[key] = enable
        return enable
    else:
        return False

class ConfigWidget(QWidget):
    def __init__(self, plugin_action):
        QWidget.__init__(self)
        
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        
        title_layout = ImageTitleLayout(self, ICON.PLUGIN, _('ePub Extended Metadata options'))
        layout.addLayout(title_layout)
        
        tabs = QTabWidget(self)
        layout.addWidget(tabs)
        
        
        # Add a horizontal layout containing the table and the buttons next to it
        contributor_layout = QVBoxLayout()
        tab_contributor = QWidget()
        tab_contributor.setLayout(contributor_layout)
        
        contributor_table_layout = QHBoxLayout()
        contributor_layout.addLayout(contributor_table_layout)
        tabs.addTab(tab_contributor, _('Contributor'))
        
        # Create a table the user can edit the menu list
        self.table = ContributorTableWidget(PREFS[KEY.CONTRIBUTORS], self)
        contributor_table_layout.addWidget(self.table)
        
        # Add a vertical layout containing the the buttons to move ad/del etc.
        button_layout = QVBoxLayout()
        contributor_table_layout.addLayout(button_layout)
        add_button = QToolButton(self)
        add_button.setToolTip(_('Add a Column/Contributor pair'))
        add_button.setIcon(get_icon('plus.png'))
        button_layout.addWidget(add_button)
        button_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        delete_button = QToolButton(self)
        delete_button.setToolTip(_('Delete Column/Contributor pair'))
        delete_button.setIcon(get_icon('minus.png'))
        button_layout.addWidget(delete_button)
        button_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        add_button.clicked.connect(self.table.add_row)
        delete_button.clicked.connect(self.table.delete_rows)
        
        
        contributor_option = QHBoxLayout()
        contributor_layout.addLayout(contributor_option)
        
        self.linkAuthors = QCheckBox(_('Embed "{:s}" column').format(FIELD.AUTHOR.COLUMN), self)
        self.linkAuthors.setToolTip(_('Embed the "{:s}" column as a Contributors metadata. This a write-only option, the import action will not change the Calibre {:s} column.').format(FIELD.AUTHOR.COLUMN, FIELD.AUTHOR.LOCAL))
        self.linkAuthors.setChecked(PREFS[KEY.LINK_AUTHOR])
        contributor_option.addWidget(self.linkAuthors)
        
        #self.creatorsAsAuthors = QCheckBox(_('Import all Creators as authors'), self)
        #self.creatorsAsAuthors.setToolTip(_('Import all Creators as {:s} in "{:s}" column.').format(FIELD.AUTHOR.LOCAL, FIELD.AUTHOR.COLUMN))
        #self.creatorsAsAuthors.setChecked(PREFS[KEY.CREATORS_AS_AUTHOR])
        #contributor_option.addWidget(self.creatorsAsAuthors)
        
        contributor_option.addStretch(1)
        
        
        # ePub 3 tab
        
        scroll_layout = QVBoxLayout()
        tab_epub3 = QWidget()
        tab_epub3.setLayout(scroll_layout)
        scrollable = QScrollArea()
        scrollable.setWidget(tab_epub3)
        scrollable.setWidgetResizable(True)
        tabs.addTab(scrollable, _('ePub3 metadata'))
        
        epub3_layout = QGridLayout()
        scroll_layout.addLayout(epub3_layout)
        epub3_layout.addWidget(QLabel('Work in progres', self), 0, 0, 1, 1)
        
        
        
        scroll_layout.addStretch(1)
        
        # Global options
        option_layout = QHBoxLayout()
        layout.addLayout(option_layout)
        
        option_layout.insertStretch(-1)
        
        self.reader_button = QPushButton(_('Automatic import'))
        self.reader_button.setToolTip(_('Allows to automatically import the extended metadata when adding a new book to the library'))
        button_plugin_initialized(self.reader_button, KEY.AUTO_IMPORT)
        option_layout.addWidget(self.reader_button)
        self.writer_button = QPushButton(_('Automatic embed'))
        self.writer_button.setToolTip(_('Allows to to automatically embed the extended metadata at the same time as the default Calibre action'))
        button_plugin_initialized(self.writer_button, KEY.AUTO_EMBED)
        option_layout.addWidget(self.writer_button)
        
        
        # --- Keyboard shortcuts ---
        keyboard_layout = QHBoxLayout()
        layout.addLayout(keyboard_layout)
        keyboard_shortcuts_button = QPushButton(_('Keyboard shortcuts...'), self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        keyboard_layout.addWidget(keyboard_shortcuts_button)
        keyboard_layout.insertStretch(-1)
        
        import_option = QPushButton(_('Edit import options'))
        if self.reader_button.isEnabled():
            p = KEY.find_plugin(KEY.AUTO_IMPORT)
            import_option.clicked.connect(partial(p.do_user_config, self))
        else:
            import_option.setEnabled(False)
        keyboard_layout.addWidget(import_option)
        
    
    def validate(self):
        valide = self.table.valide_contributors_columns()
        if not valide: warning_dialog(GUI, _('Duplicate values'),
                _('The current parameters contain duplicate values.\nYour changes can\'t be saved and have been cancelled.'),
                show=True, show_copy_button=False)
            
        return valide
    
    def save_settings(self):
        with PREFS:
            PREFS[KEY.CONTRIBUTORS] = self.table.get_contributors_columns()
            PREFS[KEY.LINK_AUTHOR] = self.linkAuthors.checkState() == Qt.Checked
            PREFS[KEY.CREATORS_AS_AUTHOR] = self.creatorsAsAuthors.checkState() == Qt.Checked
            PREFS[KEY.AUTO_IMPORT] = self.reader_button.pluginEnable
            PREFS[KEY.AUTO_EMBED] = self.writer_button.pluginEnable
            PREFS[KEY.FIRST_CONFIG] = False
            
            if PREFS[KEY.LINK_AUTHOR]:
                poped = PREFS[KEY.CONTRIBUTORS].pop(FIELD.AUTHOR.ROLE, None)
                if poped:
                    PREFS[str(len(PREFS[KEY.CONTRIBUTORS])+1)] = poped
        
        debug_print('Save settings:\n{0}\n'.format(PREFS))
        plugin_check_enable_library()
    
    def edit_shortcuts(self):
        KeyboardConfigDialog.edit_shortcuts(self.plugin_action)


def button_plugin_initialized(button, key):
    button.pluginEnable = plugin_realy_enable(key)
    if KEY.find_plugin(key):
        button.clicked.connect(partial(button_plugin_clicked, button, key))
        button_plugin_icon(button, key)
    else:
        button.setIcon(get_icon(ICON.WARNING))
        button.setEnabled(False)
        button.setToolTip(_('This feature has been incorrectly initialized. Restart Calibre to fix this.'))

def button_plugin_clicked(button, key):
    button.pluginEnable = not button.pluginEnable
    button_plugin_icon(button, key)

def button_plugin_icon(button, key):
    if button.pluginEnable:
        button.setIcon(get_icon('dot_green.png'))
    else:
        button.setIcon(get_icon('dot_red.png'))


COL_COLUMNS = [_('Contributor type'), _('Column'), '']
class ContributorTableWidget(QTableWidget):
    _columnContrib = 0
    _columnColumn = 1
    _columnSpace = 2
    
    def __init__(self, contributors_pair_list=None, *args):
        QTableWidget.__init__(self, *args)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSortingEnabled(False)
        self.setMinimumSize(600, 0)
        self.populate_table(contributors_pair_list)
    
    def populate_table(self, contributors_pair_list=None):
        self.clear()
        self.setColumnCount(len(COL_COLUMNS))
        self.setHorizontalHeaderLabels(COL_COLUMNS)
        self.verticalHeader().setDefaultSectionSize(24)
        
        contributors_pair_list = contributors_pair_list or {}
        
        if PREFS[KEY.FIRST_CONFIG] and not contributors_pair_list:
            columns = KEY.get_names()
            for role in CONTRIBUTORS_ROLES:
                for column in columns:
                    if equals_no_case('#'+role, column):
                        contributors_pair_list[role] = column
        
        self.setRowCount(len(contributors_pair_list))
        for row, contributors_pair in enumerate(iteritems(contributors_pair_list), 0):
            self.populate_table_row(row, contributors_pair)
        
        self.selectRow(0)
    
    def populate_table_row(self, row, contributors_pair):
        self.blockSignals(True)
        
        contributors_pair = contributors_pair or ('','')
        self.setCellWidget(row, self._columnContrib, ContributorsComboBox(self, contributors_pair[0]))
        self.setCellWidget(row, self._columnColumn, DuplicColumnComboBox(self, contributors_pair[1]))
        self.setItem(row, self._columnSpace, ReadOnlyTableWidgetItem(''))
        
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
        message = _('Are you sure you want to delete this Column/Contributor pair?')
        if len(rows) > 1:
            message = _('Are you sure you want to delete the selected {:d} Column/Contributor pairs?').format(len(rows))
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
    
    
    def _duplicate_entrys(self, column):
        de = duplicate_entry([ self.cellWidget(row, column).currentText() for row in range(self.rowCount()) ])
        if '' in de: de.remove('')
        return de
    
    def valide_contributors_columns(self):
        aa = self._duplicate_entrys(self._columnContrib)
        cc = self._duplicate_entrys(self._columnColumn)
        return not(aa or cc)
    
    def get_contributors_columns(self):
        contributors_columns = {}
        for row in range(self.rowCount()):
            k = self.cellWidget(row, self._columnContrib).selected_key()
            v = self.cellWidget(row, self._columnColumn).selected_column()
            
            if k or v:
                contributors_columns[k if k else str(row)] = v if v else ''
        
        return contributors_columns

class ContributorsComboBox(KeyValueComboBox):
    def __init__(self, table, selected_contributors):
        KeyValueComboBox.__init__(self, table, CONTRIBUTORS_ROLES, selected_contributors, values_ToolTip=CONTRIBUTORS_DESCRIPTION)
        self.table = table
        self.currentIndexChanged.connect(self.test_contributors_changed)
    
    def wheelEvent(self, event):
        # Disable the mouse wheel on top of the combo box changing selection as plays havoc in a grid
        event.ignore()
    
    def test_contributors_changed(self, val):
        de = self.table._duplicate_entrys(self.table._columnContrib)
        if de and de.count(self.currentText()):
            warning_dialog(self, _('Duplicate Contributors type'),
                _('A Contributor was duplicated!\nChange the settings so that each contributor is present only once, otherwise the settings can not be saved.\n\nDuplicate type:')
                + '\n' + '\n'.join(de),
                show=True, show_copy_button=False)

class DuplicColumnComboBox(CustomColumnComboBox):
    
    def __init__(self, table, selected_column):
        CustomColumnComboBox.__init__(self, table, KEY.get_names(), selected_column, initial_items=[''])
        self.table = table
        self.currentIndexChanged.connect(self.test_column_changed)
    
    def wheelEvent(self, event):
        # Disable the mouse wheel on top of the combo box changing selection as plays havoc in a grid
        event.ignore()
    
    def test_column_changed(self, val):
        de = self.table._duplicate_entrys(self.table._columnColumn)
        if de and de.count(self.currentText()):
            warning_dialog(self, _('Duplicate Custom column'),
                _('A Custom column was duplicated!\nChange the settings so that each Custom column is present only once, otherwise the settings can not be saved.\n\nDuplicate column:')
                + '\n' + '\n'.join(de),
                show=True, show_copy_button=False)



OPTION_MANUAL = OrderedDict([
    (True, _('Keep Calibre metadata, fill only the empty fields')),
    (False, _('Overwrites Calibre metadata, considers that the book always reason'))
])

OPTION_AUTO = OrderedDict([
    (True, _('Keep Calibre embed metadata that could exist in the book')),
    (False, _('Overwrites Calibre embed metadata, give priority to original metadata'))
])


class ConfigReaderWidget(QWidget):
    def __init__(self, plugin_action):
        QWidget.__init__(self)
        
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        
        title_layout = ImageTitleLayout(self, ICON.PLUGIN, _('ePub Extended Metadata import options'))
        layout.addLayout(title_layout)
        head = QLabel(_('Set here the specifics options to read and automatic addition of metadata.'))
        head.setWordWrap(True)
        layout.addWidget(head)
        
        conflict = QLabel(_('Choose the behavior to adopt in case of conflict between the metadata read by ePub Extended Metadata and the one already recorded by Calibre.'))
        conflict.setWordWrap(True)
        layout.addWidget(conflict)
        
        layout.addWidget(QLabel(''))
        
        importManual_Label = QLabel(_('When importing manually:'))
        importManual_ToolTip = _('The manual import is executed by clicking on "Import Extended Metadata" in the menu of \'ePub Extended Metadata\'')
        importManual_Label.setToolTip(importManual_ToolTip)
        layout.addWidget(importManual_Label)
        self.importManual = KeyValueComboBox(self, OPTION_MANUAL, PREFS[KEY.KEEP_CALIBRE_MANUAL])
        self.importManual.setToolTip(importManual_ToolTip)
        layout.addWidget(self.importManual)
        
        importAuto_Label = QLabel(_('During automatic import:'))
        importAuto_ToolTip = _('The auto import is executed when Calibre add a book to the library')
        importAuto_Label.setToolTip(importAuto_ToolTip)
        layout.addWidget(importAuto_Label)
        self.importAuto = KeyValueComboBox(self, OPTION_AUTO, PREFS[KEY.KEEP_CALIBRE_AUTO])
        self.importAuto.setToolTip(importAuto_ToolTip)
        layout.addWidget(self.importAuto)
        
        layout.insertStretch(-1)
    
    
    def save_settings(self):
        prefs = {}
        prefs[KEY.KEEP_CALIBRE_AUTO] = self.importAuto.selected_key()
        prefs[KEY.KEEP_CALIBRE_MANUAL] = self.importManual.selected_key()
        
        PREFS.update(prefs)
        debug_print('Save settings of import:\n{0}\n'.format(prefs))
        plugin_check_enable_library()
    