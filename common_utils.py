#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake <grant.drake@gmail.com>'
__docformat__ = 'restructuredtext en'

import os, sys, copy, time
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

try: #polyglot added in calibre 4.0
    from polyglot.builtins import iteritems, itervalues
except ImportError:
    def iteritems(d):
        return d.iteritems()
    def itervalues(d):
        return d.itervalues()

try:
    from qt.core import (Qt, QIcon, QPixmap, QLabel, QDialog, QHBoxLayout,
                            QTableWidgetItem, QFont, QLineEdit, QComboBox,
                            QVBoxLayout, QDialogButtonBox, QStyledItemDelegate, QDateTime,
                            QTextEdit, QListWidget, QAbstractItemView, QApplication)
    
except ImportError:
    from PyQt5.Qt import (Qt, QIcon, QPixmap, QLabel, QDialog, QHBoxLayout,
                            QTableWidgetItem, QFont, QLineEdit, QComboBox,
                            QVBoxLayout, QDialogButtonBox, QStyledItemDelegate, QDateTime,
                            QTextEdit, QListWidget, QAbstractItemView, QApplication)

from calibre import prints
from calibre.constants import iswindows, DEBUG, numeric_version as calibre_version
from calibre.gui2 import gprefs, error_dialog, info_dialog, show_restart_warning, UNDEFINED_QDATETIME
from calibre.gui2.actions import menu_action_unique_name
from calibre.gui2.complete2 import EditWithComplete
from calibre.gui2.ui import get_gui
from calibre.gui2.keyboard import ShortcutConfig
from calibre.gui2.widgets import EnLineEdit
from calibre.utils.config import config_dir, JSONConfig, tweaks, DynamicConfig
from calibre.utils.date import now, format_date, qt_to_dt, UNDEFINED_DATE
from calibre.utils.icu import sort_key


PYTHON = sys.version_info

GUI = get_gui()


def get__init__attribut(name, default=None, use_root_has_default=False):
    '''
    Retrieve a attribut at the root plugin (in __init__.py)
    '''
    ns = __name__.split('.')
    ns.pop(-1)
    
    if use_root_has_default:
        default = ns[-1]
    
    import importlib
    return getattr(importlib.import_module('.'.join(ns)), name, default)

def get_plugin_attribut(name, default=None):
        ns = __name__.split('.')
        ns.pop(-1)
        ns = '.'.join(ns)
        import importlib
        m = importlib.import_module(ns)
        from calibre.customize.ui import _initialized_plugins
        for p in _initialized_plugins:
            if ns == p.__module__:
                if hasattr(m, p.__class__.__name__):
                    return getattr(p, name, default)
        
        raise EnvironmentError('The plugin could not be found.')


DEBUG_PRE = get__init__attribut('DEBUG_PRE', use_root_has_default=True)
BASE_TIME = None
def debug_print(*args):
    
    global BASE_TIME
    if BASE_TIME is None:
        BASE_TIME = time.time()
    
    if DEBUG:
        prints('DEBUG', DEBUG_PRE+':', *args)
        #prints('DEBUG', DEBUG_PRE+': %6.1f'%(time.time()-BASE_TIME), *args)


def equals_no_case(left, right):
    if PYTHON >= (3, 3):
        return left.casefold() == right.casefold()
    else:
        return left.upper().lower() == right.upper().lower()

def duplicate_entry(lst):
    return list( set([x for x in lst if lst.count(x) > 1]) )


PREFS_NAMESPACE = get__init__attribut('PREFS_NAMESPACE', use_root_has_default=True)


# Global definition of our plugin name. Used for common functions that require this.
PLUGIN_NAME = get_plugin_attribut('name')

# Global definition of our plugin resources. Used to share between the xxxAction and xxxBase
# classes if you need any zip images to be displayed on the configuration dialog.
PLUGIN_RESOURCES = {}

THEME_COLOR = ['', 'dark', 'light']

def get_theme_color():
    if calibre_version > (5, 90) and 'user-any' in QIcon.themeName():
        return THEME_COLOR[1] if QApplication.instance().is_dark_theme else THEME_COLOR[2]
    return THEME_COLOR[0]

def get_icon_themed(icon_name, theme_color=None):
    theme_color = theme_color if theme_color != None else get_theme_color()
    return icon_name.replace('/', '/'+theme_color+'/', 1).replace('//', '/')

def load_plugin_resources(plugin_path, names=[]):
    '''
    Set our global store of plugin name and icon resources for sharing between
    the InterfaceAction class which reads them and the ConfigWidget
    if needed for use on the customization dialog for this plugin.
    '''
    names = names or []
    
    if plugin_path is None:
        raise ValueError('This plugin was not loaded from a ZIP file')
    ans = {}
    from calibre.utils.zipfile import ZipFile
    with ZipFile(plugin_path, 'r') as zf:
        lst = zf.namelist()
        for name in names:
            for color in THEME_COLOR:
                themed = get_icon_themed(name, color)
                if themed in lst:
                    ans[themed] = zf.read(themed)
    
    global PLUGIN_RESOURCES
    PLUGIN_RESOURCES.update(ans)

def get_icon(icon_name=None):
    '''
    Retrieve a QIcon for the named image from the zip file if it exists,
    or if not then from Calibre's image cache.
    '''
    def themed_icon(icon_name):
        if calibre_version < (5, 90):
            return QIcon(I(icon_name))
        else:
            return QIcon.ic(icon_name)
    
    if icon_name:
        pixmap = get_pixmap(icon_name)
        if pixmap is None:
            # Look in Calibre's cache for the icon
            return themed_icon(icon_name)
        else:
            return QIcon(pixmap)
    return QIcon()

def get_pixmap(icon_name):
    '''
    Retrieve a QPixmap for the named image
    Any icons belonging to the plugin must be prefixed with 'images/'
    '''
    
    if not icon_name.startswith('images/'):
        # We know this is definitely not an icon belonging to this plugin
        pixmap = QPixmap()
        pixmap.load(I(icon_name))
        return pixmap
    
    # Build the icon_name according to the theme of the OS or Qt
    icon_themed = get_icon_themed(icon_name)
    
    # Check to see whether the icon exists as a Calibre resource
    # This will enable skinning if the user stores icons within a folder like:
    # ...\AppData\Roaming\calibre\resources\images\Plugin Name\
    def get_from_local(name):
        local_images_dir = get_local_images_dir(PLUGIN_NAME)
        local_image_path = os.path.join(local_images_dir, name.replace('images/', ''))
        if os.path.exists(local_image_path):
            pxm = QPixmap()
            pxm.load(local_image_path)
            return pxm
        return None
    
    if PLUGIN_NAME:
        pixmap = get_from_local(icon_themed)
        if not pixmap:
            pixmap = get_from_local(icon_name)
        if pixmap:
            return pixmap
    
    ##
    # As we did not find an icon elsewhere, look within our zip resources
    global PLUGIN_RESOURCES
    def get_from_resources(name):
        if name in PLUGIN_RESOURCES:
            pxm = QPixmap()
            pxm.loadFromData(PLUGIN_RESOURCES[name])
            return pxm
        return None
    
    pixmap = get_from_resources(icon_themed)
    if not pixmap:
        pixmap = get_from_resources(icon_name)
    if pixmap:
        return pixmap
    
    return None

def get_local_images_dir(subfolder=None):
    '''
    Returns a path to the user's local resources/images folder
    If a subfolder name parameter is specified, appends this to the path
    '''
    images_dir = os.path.join(config_dir, 'resources/images')
    if subfolder:
        images_dir = os.path.join(images_dir, subfolder.replace('/','-'))
    
    if iswindows:
        images_dir = os.path.normpath(images_dir)
    return images_dir


def current_db():
    '''
    Safely provides the current_db or None
    '''
    return getattr(get_gui(),'current_db', None)

def get_library_uuid(db=None):
    db = db or current_db()
    try:
        library_uuid = db.library_id
    except:
        library_uuid = ''
    return library_uuid


def get_selected_BookIds(show_error=True, msg=None):
    ids = []
    try:
        rows = GUI.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            ids = []
            
            if show_error:
                title = _('No book selected')
                error_dialog(GUI, title, title +'\n'+ _('Could not to launch {:s}').format(PLUGIN_NAME), show=True, show_copy_button=False)
            
        else:
            ids = GUI.library_view.get_selected_ids()
    except Exception as err:
        debug_print(err)
        CustomExceptionErrorDialog(err)
        ids = []
    
    return ids

def create_menu_item(ia, parent_menu, menu_text, image=None, tooltip=None,
                     shortcut=(), triggered=None, is_checked=None):
    '''
    Create a menu action with the specified criteria and action
    Note that if no shortcut is specified, will not appear in Preferences->Keyboard
    This method should only be used for actions which either have no shortcuts,
    or register their menus only once. Use create_menu_action_unique for all else.
    '''
    if shortcut is not None:
        if len(shortcut) == 0:
            shortcut = ()
        else:
            shortcut = _(shortcut)
    ac = ia.create_action(spec=(menu_text, None, tooltip, shortcut),
        attr=menu_text)
    if image:
        ac.setIcon(get_icon(image))
    if triggered is not None:
        ac.triggered.connect(triggered)
    if is_checked is not None:
        ac.setCheckable(True)
        if is_checked:
            ac.setChecked(True)
    
    parent_menu.addAction(ac)
    return ac

def create_menu_action_unique(ia, parent_menu, menu_text, image=None, tooltip=None,
                              shortcut=None, shortcut_name=None, triggered=None, is_checked=None,
                              unique_name=None, favourites_menu_unique_name=None,submenu=None, enabled=True):
    '''
    Create a menu action with the specified criteria and action, using the new
    InterfaceAction.create_menu_action() function which ensures that regardless of
    whether a shortcut is specified it will appear in Preferences->Keyboard
    '''
    orig_shortcut = shortcut
    kb = GUI.keyboard
    unique_name = unique_name or menu_text
        
    if not shortcut == False:
        full_unique_name = menu_action_unique_name(ia, unique_name)
        if full_unique_name in kb.shortcuts:
            shortcut = False
        else:
            if shortcut is not None and not shortcut == False:
                if len(shortcut) == 0:
                    shortcut = None
                else:
                    shortcut = _(shortcut)
    
    shortcut_name = shortcut_name = menu_text.replace('&','')
    
    ac = ia.create_menu_action(parent_menu, unique_name, menu_text, icon=None, shortcut=shortcut,
        description=tooltip, triggered=triggered, shortcut_name=shortcut_name)
    if shortcut == False and not orig_shortcut == False:
        if ac.calibre_shortcut_unique_name in GUI.keyboard.shortcuts:
            kb.replace_action(ac.calibre_shortcut_unique_name, ac)
    if image:
        ac.setIcon(get_icon(image))
    if is_checked is not None:
        ac.setCheckable(True)
        if is_checked:
            ac.setChecked(True)
            
    if submenu:
        ac.setMenu(submenu)
        
    if not enabled:
        ac.setEnabled(False)
    else:
        ac.setEnabled(True)
    return ac


def has_restart_pending(show_warning=True, msg_warning=None):
    restart_pending = GUI.must_restart_before_config
    if restart_pending and show_warning:
        msg = msg_warning if msg_warning else _('You cannot configure this plugin before calibre is restarted.')
        if show_restart_warning(msg):
            GUI.quit(restart=True)
    return restart_pending


class ImageTitleLayout(QHBoxLayout):
    '''
    A reusable layout widget displaying an image followed by a title
    '''
    def __init__(self, parent, icon_name, title):
        QHBoxLayout.__init__(self)
        self.title_image_label = QLabel(parent)
        self.update_title_icon(icon_name)
        self.addWidget(self.title_image_label)
        
        title_font = QFont()
        title_font.setPointSize(16)
        shelf_label = QLabel(title, parent)
        shelf_label.setFont(title_font)
        self.addWidget(shelf_label)
        self.insertStretch(-1)
    
    def update_title_icon(self, icon_name):
        pixmap = get_pixmap(icon_name)
        if pixmap is None:
            error_dialog(self.parent(), _('Restart required'),
                         _('Title image not found - you must restart Calibre before using this plugin!'), show=True)
        else:
            self.title_image_label.setPixmap(pixmap)
        self.title_image_label.setMaximumSize(32, 32)
        self.title_image_label.setScaledContents(True)

class SizePersistedDialog(QDialog):
    '''
    This dialog is a base class for any dialogs that want their size/position
    restored when they are next opened.
    '''
    def __init__(self, parent, unique_pref_name):
        QDialog.__init__(self, parent)
        self.unique_pref_name = unique_pref_name
        self.geom = gprefs.get(unique_pref_name, None)
        self.finished.connect(self.dialog_closing)
    
    def resize_dialog(self):
        if self.geom is None:
            self.resize(self.sizeHint())
        else:
            self.restoreGeometry(self.geom)
    
    def dialog_closing(self, result):
        geom = bytearray(self.saveGeometry())
        gprefs[self.unique_pref_name] = geom
        self.persist_custom_prefs()
    
    def persist_custom_prefs(self):
        '''
        Invoked when the dialog is closing. Override this function to call
        save_custom_pref() if you have a setting you want persisted that you can
        retrieve in your __init__() using load_custom_pref() when next opened
        '''
        pass
    
    def load_custom_pref(self, name, default=None):
        return gprefs.get(self.unique_pref_name+':'+name, default)
    
    def save_custom_pref(self, name, value):
        gprefs[self.unique_pref_name+':'+name] = value


class ReadOnlyTableWidgetItem(QTableWidgetItem):
    def __init__(self, text):
        text = text or ''
        QTableWidgetItem.__init__(self, text)
        self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)

class RatingTableWidgetItem(QTableWidgetItem):
    def __init__(self, rating, is_read_only=False):
        QTableWidgetItem.__init__(self, '')
        self.setData(Qt.DisplayRole, rating)
        if is_read_only:
            self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)

class DateTableWidgetItem(QTableWidgetItem):
    def __init__(self, date_read, is_read_only=False, default_to_today=False, fmt=None):
        if date_read == UNDEFINED_DATE and default_to_today:
            date_read = now()
        if is_read_only:
            QTableWidgetItem.__init__(self, format_date(date_read, fmt))
            self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        else:
            QTableWidgetItem.__init__(self, '')
            dt = UNDEFINED_QDATETIME if date_read is None else QDateTime(date_read)
            self.setData(Qt.DisplayRole, dt)

class CheckableTableWidgetItem(QTableWidgetItem):
    def __init__(self, checked=False, is_tristate=False):
        QTableWidgetItem.__init__(self, '')
        self.setFlags(Qt.ItemFlag(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled ))
        if is_tristate:
            self.setFlags(self.flags() | Qt.ItemIsTristate)
        if checked:
            self.setCheckState(Qt.Checked)
        else:
            if is_tristate and checked is None:
                self.setCheckState(Qt.PartiallyChecked)
            else:
                self.setCheckState(Qt.Unchecked)
    
    def get_boolean_value(self):
        '''
        Return a boolean value indicating whether checkbox is checked
        If this is a tristate checkbox, a partially checked value is returned as None
        '''
        if self.checkState() == Qt.PartiallyChecked:
            return None
        else:
            return self.checkState() == Qt.Checked

class TextIconWidgetItem(QTableWidgetItem):
    def __init__(self, text, icon, tooltip=None, is_read_only=False):
        QTableWidgetItem.__init__(self, text)
        if icon:
            self.setIcon(icon)
        if tooltip:
            self.setToolTip(tooltip)
        if is_read_only:
            self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)

class ReadOnlyTextIconWidgetItem(ReadOnlyTableWidgetItem):
    def __init__(self, text, icon):
        ReadOnlyTableWidgetItem.__init__(self, text)
        if icon: self.setIcon(icon)


class ReadOnlyLineEdit(QLineEdit):
    def __init__(self, text, parent):
        text = text or ''
        QLineEdit.__init__(self, text, parent)
        self.setEnabled(False)

class NoWheelComboBox(QComboBox):
    
    def wheelEvent(self, event):
        # Disable the mouse wheel on top of the combo box changing selection as plays havoc in a grid
        event.ignore()

class ImageComboBox(NoWheelComboBox):
    def __init__(self, parent, image_map, selected_text):
        NoWheelComboBox.__init__(self, parent)
        self.populate_combo(image_map, selected_text)
    
    def populate_combo(self, image_map, selected_text):
        self.clear()
        for i, image in enumerate(get_image_names(image_map), 0):
            self.insertItem(i, image_map.get(image, image), image)
        idx = self.findText(selected_text)
        self.setCurrentIndex(idx)
        self.setItemData(0, idx)

class ListComboBox(QComboBox):
    def __init__(self, parent, values, selected_value=None):
        QComboBox.__init__(self, parent)
        self.values = values
        if selected_value is not None:
            self.populate_combo(selected_value)
    
    def populate_combo(self, selected_value):
        self.clear()
        selected_idx = idx = -1
        for value in self.values:
            idx = idx + 1
            self.addItem(value)
            if value == selected_value:
                selected_idx = idx
        self.setCurrentIndex(selected_idx)
    
    def selected_value(self):
        return unicode(self.currentText())

class KeyValueComboBox(QComboBox):
    def __init__(self, parent, values, selected_key=None, values_ToolTip={}):
        QComboBox.__init__(self, parent)
        self.populate_combo(values, selected_key, values_ToolTip)
        self.refresh_ToolTip()
        self.currentIndexChanged.connect(self.key_value_changed)
    
    def populate_combo(self, values, selected_key=None, values_ToolTip={}):
        self.clear()
        self.values_ToolTip = values_ToolTip
        self.values = values
        
        selected_idx = start = 0
        for idx, (key, value) in enumerate(iteritems(self.values), start):
            self.addItem(value)
            if key == selected_key:
                selected_idx = idx
        
        self.setCurrentIndex(selected_idx)
    
    def selected_key(self):
        currentText = unicode(self.currentText()).strip()
        for key, value in iteritems(self.values):
            if value == currentText:
                return key
    
    def key_value_changed(self, val):
        self.refresh_ToolTip()
    
    def refresh_ToolTip(self):
        if self.values_ToolTip:
            self.setToolTip(self.values_ToolTip.get(self.selected_key(), ''))


class CustomColumnComboBox(QComboBox):
    def __init__(self, parent, custom_columns, selected_column='', initial_items=['']):
        QComboBox.__init__(self, parent)
        self.populate_combo(custom_columns, selected_column, initial_items)
        self.refresh_ToolTip()
        self.currentIndexChanged.connect(self.column_changed)
    
    def populate_combo(self, custom_columns, selected_column='', initial_items=['']):
        self.clear()
        self.custom_columns = custom_columns
        self.column_names = list()
        initial_items = initial_items or []
        
        selected_idx = start = 0
        for start, init in enumerate(initial_items, 1):
            self.column_names.append(init)
            self.addItem(init)
        
        for idx, (key, value) in enumerate(iteritems(self.custom_columns), start):
            self.column_names.append(key)
            self.addItem('{:s} ({:s})'.format(key, value.display_name))
            if key == selected_column:
                selected_idx = idx
        
        self.setCurrentIndex(selected_idx)
    
    def selected_column(self):
        return self.column_names[self.currentIndex()]
    
    def column_changed(self, val):
        self.refresh_ToolTip()
    
    def refresh_ToolTip(self):
        cc = self.custom_columns.get(self.selected_column(), None)
        if cc:
            self.setToolTip(cc.description)
        else:
            self.setToolTip('')

class ReorderedComboBox(QComboBox):
    def __init__(self, parent, strip_items=True):
        QComboBox.__init__(self, parent)
        self.strip_items = strip_items
        self.setEditable(True)
        self.setMaxCount(10)
        self.setInsertPolicy(QComboBox.InsertAtTop)
    
    def populate_items(self, items, sel_item):
        self.blockSignals(True)
        self.clear()
        self.clearEditText()
        for text in items:
            if text != sel_item:
                self.addItem(text)
        if sel_item:
            self.insertItem(0, sel_item)
            self.setCurrentIndex(0)
        else:
            self.setEditText('')
        self.blockSignals(False)
    
    def reorder_items(self):
        self.blockSignals(True)
        text = unicode(self.currentText())
        if self.strip_items:
            text = text.strip()
        if not text.strip():
            return
        existing_index = self.findText(text, Qt.MatchExactly)
        if existing_index:
            self.removeItem(existing_index)
            self.insertItem(0, text)
            self.setCurrentIndex(0)
        self.blockSignals(False)
    
    def get_items_list(self):
        if self.strip_items:
            return [unicode(self.itemText(i)).strip() for i in range(0, self.count())]
        else:
            return [unicode(self.itemText(i)) for i in range(0, self.count())]

class DragDropLineEdit(QLineEdit):
    '''
    Unfortunately there is a flaw in the Qt implementation which means that
    when the QComboBox is in editable mode that dropEvent is not fired
    if you drag into the editable text area. Working around this by having
    a custom LineEdit() set for the parent combobox.
    '''
    def __init__(self, parent, drop_mode):
        QLineEdit.__init__(self, parent)
        self.drop_mode = drop_mode
        self.setAcceptDrops(True)
    
    def dragMoveEvent(self, event):
        event.acceptProposedAction()
    
    def dragEnterEvent(self, event):
        if int(event.possibleActions() & Qt.CopyAction) + \
           int(event.possibleActions() & Qt.MoveAction) == 0:
            return
        data = self._get_data_from_event(event)
        if data:
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        data = self._get_data_from_event(event)
        event.setDropAction(Qt.CopyAction)
        self.setText(data[0])
    
    def _get_data_from_event(self, event):
        md = event.mimeData()
        if self.drop_mode == 'file':
            urls, filenames = dnd_get_files(md, ['csv', 'txt'])
            if not urls:
                # Nothing found
                return
            if not filenames:
                # Local files
                return urls
            else:
                # Remote files
                return filenames
        if event.mimeData().hasFormat('text/uri-list'):
            urls = [unicode(u.toString()).strip() for u in md.urls()]
            return urls

class DragDropComboBox(ReorderedComboBox):
    '''
    Unfortunately there is a flaw in the Qt implementation which means that
    when the QComboBox is in editable mode that dropEvent is not fired
    if you drag into the editable text area. Working around this by having
    a custom LineEdit() set for the parent combobox.
    '''
    def __init__(self, parent, drop_mode='url'):
        ReorderedComboBox.__init__(self, parent)
        self.drop_line_edit = DragDropLineEdit(parent, drop_mode)
        self.setLineEdit(self.drop_line_edit)
        self.setAcceptDrops(True)
        self.setEditable(True)
        self.setMaxCount(10)
        self.setInsertPolicy(QComboBox.InsertAtTop)
    
    def dragMoveEvent(self, event):
        self.lineEdit().dragMoveEvent(event)
    
    def dragEnterEvent(self, event):
        self.lineEdit().dragEnterEvent(event)
    
    def dropEvent(self, event):
        self.lineEdit().dropEvent(event)


class KeyboardConfigDialog(SizePersistedDialog):
    '''
    This dialog is used to allow editing of keyboard shortcuts.
    '''
    def __init__(self, group_name):
        SizePersistedDialog.__init__(self, GUI, _('Keyboard shortcut dialog'))
        self.setWindowTitle(_('Keyboard shortcuts'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        
        self.keyboard_widget = ShortcutConfig(self)
        layout.addWidget(self.keyboard_widget)
        self.group_name = group_name
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.commit)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()
        self.initialize()
    
    def initialize(self):
        self.keyboard_widget.initialize(GUI.keyboard)
        self.keyboard_widget.highlight_group(self.group_name)
    
    def commit(self):
        self.keyboard_widget.commit()
        self.accept()
    
    @staticmethod
    def edit_shortcuts(plugin_action):
        getattr(plugin_action, 'rebuild_menus', ())()
        d = KeyboardConfigDialog(plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            GUI.keyboard.finalize()


import re
# Simple Regex
class regex():
    
    def __init__(self, flag=None):
        
        #set the default flag
        self.flag = flag
        if not self.flag:
            if PYTHON[0] == 2:
                self.flag = re.MULTILINE + re.DOTALL
            else:
                self.flag = re.ASCII + re.MULTILINE + re.DOTALL
                # calibre 5 // re.ASCII for Python3 only
            
    
    def match(self, pattern, string, flag=None):
        flag = flag or self.flag
        return re.fullmatch(pattern, string, flag)
    
    def search(self, pattern, string, flag=None):
        flag = flag or self.flag
        return re.search(pattern, string, flag)
    
    def searchall(self, pattern, string, flag=None):
        flag = flag or self.flag
        if self.search(pattern, string, flag):
            return re.finditer(pattern, string, flag)
        else:
            return None
    
    def split(self, pattern, string, maxsplit=0, flag=None):
        flag = flag or self.flag
        return re.split(pattern, string, maxsplit, flag)
    
    def simple(self, pattern, repl, string, flag=None):
        flag = flag or self.flag
        return re.sub(pattern, repl, string, 0, flag)
    
    def loop(self, pattern, repl, string, flag=None):
        flag = flag or self.flag
        i = 0
        while self.search(pattern, string, flag):
            if i > 1000:
                raise regexException('the pattern and substitution string caused an infinite loop', pattern, repl)
            string = self.simple(pattern, repl, string, flag)
            i+=1
            
        return string

class regexException(BaseException):
    def __init__(self, msg, pattern=None, repl=None):
        self.pattern = pattern
        self.repl = repl
        self.msg = msg
    
    def __str__(self):
        return self.msg


def CSS_CleanRules(css):
    #remove space and invalid character
    r = regex()
    css = r.loop(r'[.*!()?+<>\\]', r'', css.lower())
    css = r.loop(r'(,|;|:|\n|\r|\s{2,})', r' ', css)
    css = r.simple(r'^\s*(.*?)\s*$', r'\1', css); 
    # split to table and remove duplicate
    css = list(dict.fromkeys(css.split(' ')))
    # sort
    css = sorted(css)
    # join in a string
    css = ' '.join(css)
    return css

def CustomExceptionErrorDialog(exception, custome_title=None, custome_msg=None, show=True):
    
    from polyglot.io import PolyglotStringIO
    import traceback
    from calibre import as_unicode, prepare_string_for_xml
    
    sio = PolyglotStringIO(errors='replace')
    try:
        from calibre.debug import print_basic_debug_info
        print_basic_debug_info(out=sio)
    except:
        pass
    
    try:
        traceback.print_exception(type(exception), exception, exception.__traceback__, file=sio)
    except:
        traceback.print_exception(type(exception), exception, sys.exc_traceback, file=sio)
        pass
    
    fe = sio.getvalue()
    
    if not custome_title:
        custome_title = _('Unhandled exception')
    
    if custome_msg:
        custome_msg = '<span>' + prepare_string_for_xml(as_unicode(custome_msg +'\n')).replace('\n', '<br>')
    else:
        custome_msg = '<span>' + prepare_string_for_xml(as_unicode(_('The {:s} plugin has encounter a unhandled exception.').format(PLUGIN_NAME)+'\n')).replace('\n', '<br>')
    
    msg = custome_msg + '<b>{:s}</b>: '.format(exception.__class__.__name__) + prepare_string_for_xml(as_unicode(str(exception)))
    
    return error_dialog(GUI, custome_title, msg, det_msg=fe, show=show, show_copy_button=True)


class PREFS_json(JSONConfig):
    '''
    Use plugin name to create a JSONConfig file
    to store the preferences for plugin
    '''
    def __init__(self):
        JSONConfig.__init__(self, 'plugins/'+PLUGIN_NAME)
    
    def update(self, other, **kvargs):
        JSONConfig.update(self, other, **kvargs)
        self.commit()
    
    def __call__(self):
        self.refresh()
        return self
    
    def deepcopy_dict(self):
        '''
        get a deepcopy dict of this instance
        '''
        rslt = {}
        for k,v in iteritems(self):
            rslt[copy.deepcopy(k)] = copy.deepcopy(v)
        
        for k, v in iteritems(self.defaults):
            if k not in rslt:
                rslt[k] = copy.deepcopy(v)
        return rslt

class PREFS_dynamic(DynamicConfig):
    '''
    Use plugin name to create a DynamicConfig file
    to store the preferences for plugin
    '''
    def __init__(self):
        self.no_commit = False
        DynamicConfig.__init__(self, 'plugins/'+PLUGIN_NAME)
    
    def commit(self):
        if self.no_commit:
            return
        DynamicConfig.commit(self)
    
    def __enter__(self):
        self.no_commit = True

    def __exit__(self, *args):
        self.no_commit = False
        self.commit()
    
    def __call__(self):
        self.refresh()
        return self
    
    def update(self, other, **kvargs):
        DynamicConfig.update(self, other, **kvargs)
        self.commit()
    
    def deepcopy_dict(self):
        '''
        get a deepcopy dict of this instance
        '''
        rslt = {}
        for k,v in iteritems(self):
            rslt[copy.deepcopy(k)] = copy.deepcopy(v)
        
        for k, v in iteritems(self.defaults):
            if k not in rslt:
                rslt[k] = copy.deepcopy(v)
        return rslt

class PREFS_library(dict):
    '''
    Create a dictionary of preference stored in the library
    '''
    def __init__(self, key='settings', defaults={}):
        self.no_commit = False
        self._db = None
        self.key = key if key else ''
        self.defaults = defaults if defaults else {}
        
        if not isinstance(key, unicode) and not isinstance(key, str):
            raise TypeError("The 'key' for the namespaced preference is not a string")
            
        if not isinstance(defaults, dict):
            raise TypeError("The 'defaults' for the namespaced preference is not a dict")
        
        self._namespace = PREFS_NAMESPACE
        
        self.refresh()
        dict.__init__(self)
    
    @property
    def namespace(self):
        '''
        Defined a custom namespaced at the root of __init__.py // __init__.PREFS_NAMESPACE
        '''
        return self._namespace
    
    def __getitem__(self, key):
        self.refresh()
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.defaults[key]
    
    def get(self, key, default=None):
        self.refresh()
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.defaults.get(key, default)
    
    def __setitem__(self, key, val):
        self.refresh()
        dict.__setitem__(self, key, val)
        self.commit()
    
    def set(self, key, val):
        self.__setitem__(key, val)
    
    def __delitem__(self, key):
        self.refresh()
        try:
            dict.__delitem__(self, key)
        except KeyError:
            pass  # ignore missing keys
        self.commit()
    
    def __str__(self):
        self.refresh()
        return dict.__str__(self.deepcopy_dict())
    
    def refresh(self):
        new_db = current_db()
        if new_db and self._db != new_db:
            self._db = new_db
            self.clear()
            rslt = self._db.prefs.get_namespaced(self.namespace, self.key, {})
            self.no_commit = True
            self.update(rslt)
            self.no_commit = False
    
    def commit(self):
        if self.no_commit:
            return
        self.refresh()
        
        self._db.prefs.set_namespaced(self.namespace, self.key, self.deepcopy_dict())
        self.refresh()
    
    def __enter__(self):
        self.no_commit = True
        self.refresh()
    
    def __exit__(self, *args):
        self.no_commit = False
        self.commit()
    
    def __call__(self):
        self.refresh()
        return self
    
    def update(self, other, **kvargs):
        dict.update(self, other, **kvargs)
        self.commit()
    
    def deepcopy_dict(self):
        '''
        get a deepcopy dict of this instance
        '''
        rslt = {}
        for k,v in iteritems(self):
            rslt[copy.deepcopy(k)] = copy.deepcopy(v)
        
        for k, v in iteritems(self.defaults):
            if k not in rslt:
                rslt[k] = copy.deepcopy(v)
        return rslt


def decorators(*args):
    def wrapper(func):
        for deco in args[::-1]:
            func=deco(func)
        func._decorators=args
        return func
    return wrapper

#class Foo(object):
#    @many
#    @decos
#    @here
#    def bar(self):
#        pass

#class Foo(object):
#    @decorators(many,decos,here)
#    def bar(self):
#        pass

#print(foo.bar._decorators)
# (<function many at 0xb76d9d14>, <function decos at 0xb76d9d4c>, <function here at 0xb76d9d84>)


def get_decorators_names(func):
    """Returns list of decorators names

    Args:
        func (Callable): decorated method/function

    Return:
        List of decorators as strings

    Example:
        Given:

        @my_decorator
        @another_decorator
        def decorated_function():
            pass

        >>> get_decorators(decorated_function)
        ['@my_decorator', '@another_decorator']

    """
    import inspect
    source = inspect.getsource(func)
    index = source.find("def ")
    return [
        line.strip().split()[0]
        for line in source[:index].strip().splitlines()
        if line.strip()[0] == "@"
    ]
