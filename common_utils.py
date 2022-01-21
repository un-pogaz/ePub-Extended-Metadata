#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake <grant.drake@gmail.com>'
__docformat__ = 'restructuredtext en'

import os, sys, copy, time
# calibre Python 3 compatibility.
from six import text_type as unicode

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

try:
    from qt.core import (Qt, QIcon, QPixmap, QLabel, QDialog, QHBoxLayout,
                            QTableWidgetItem, QFont, QLineEdit, QComboBox,
                            QVBoxLayout, QDialogButtonBox, QStyledItemDelegate, QDateTime,
                            QTextEdit, QListWidget, QAbstractItemView)
    
except ImportError:
    from PyQt5.Qt import (Qt, QIcon, QPixmap, QLabel, QDialog, QHBoxLayout,
                            QTableWidgetItem, QFont, QLineEdit, QComboBox,
                            QVBoxLayout, QDialogButtonBox, QStyledItemDelegate, QDateTime,
                            QTextEdit, QListWidget, QAbstractItemView)


from calibre import prints
from calibre.constants import iswindows, DEBUG
from calibre.gui2 import gprefs, error_dialog, UNDEFINED_QDATETIME, info_dialog
from calibre.gui2.actions import menu_action_unique_name
from calibre.gui2.complete2 import EditWithComplete
from calibre.gui2.ui import get_gui
from calibre.gui2.keyboard import ShortcutConfig
from calibre.gui2.widgets import EnLineEdit
from calibre.utils.config import config_dir, tweaks
from calibre.utils.date import now, format_date, qt_to_dt, UNDEFINED_DATE
from calibre.utils.icu import sort_key


PYTHON = sys.version_info
GUI = get_gui()

# Global definition of our plugin name. Used for common functions that require this.
plugin_name = None
# Global definition of our plugin resources. Used to share between the xxxAction and xxxBase
# classes if you need any zip images to be displayed on the configuration dialog.
plugin_icon_resources = {}

def get__init__attribut(name, default=None):
    '''
    Retrieve a custom global values at the root of __init__.py // __init__.name
    '''
    ns = __name__.split('.')
    ns.pop(-1)
    
    import importlib
    rslt = getattr(importlib.import_module('.'.join(ns)), name, default)
    
    if not rslt: #if no attribut and no default, use module name
        rslt = ns[-1]
    return rslt

'''
Defined a custom prefix of this plugin at the root of __init__.py // __init__.DEBUG_PRE
'''
DEBUG_PRE = get__init__attribut('DEBUG_PRE')
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


def set_plugin_icon_resources(name, resources):
    '''
    Set our global store of plugin name and icon resources for sharing between
    the InterfaceAction class which reads them and the ConfigWidget
    if needed for use on the customization dialog for this plugin.
    '''
    global plugin_icon_resources, plugin_name
    plugin_name = name
    plugin_icon_resources = resources

def get_icon(icon_name=None):
    '''
    Retrieve a QIcon for the named image from the zip file if it exists,
    or if not then from Calibre's image cache.
    '''
    if icon_name:
        pixmap = get_pixmap(icon_name)
        if pixmap is None:
            # Look in Calibre's cache for the icon
            return QIcon(I(icon_name))
        else:
            return QIcon(pixmap)
    return QIcon()

def get_pixmap(icon_name):
    '''
    Retrieve a QPixmap for the named image
    Any icons belonging to the plugin must be prefixed with 'images/'
    '''
    global plugin_icon_resources, plugin_name
    
    if not icon_name.startswith('images/'):
        # We know this is definitely not an icon belonging to this plugin
        pixmap = QPixmap()
        pixmap.load(I(icon_name))
        return pixmap
    
    # Check to see whether the icon exists as a Calibre resource
    # This will enable skinning if the user stores icons within a folder like:
    # ...\AppData\Roaming\calibre\resources\images\Plugin Name\
    if plugin_name:
        local_images_dir = get_local_images_dir(plugin_name)
        local_image_path = os.path.join(local_images_dir, icon_name.replace('images/', ''))
        if os.path.exists(local_image_path):
            pixmap = QPixmap()
            pixmap.load(local_image_path)
            return pixmap
    
    # As we did not find an icon elsewhere, look within our zip resources
    if icon_name in plugin_icon_resources:
        pixmap = QPixmap()
        pixmap.loadFromData(plugin_icon_resources[icon_name])
        return pixmap
    return None

def get_local_images_dir(subfolder=None):
    '''
    Returns a path to the user's local resources/images folder
    If a subfolder name parameter is specified, appends this to the path
    '''
    images_dir = os.path.join(config_dir, 'resources/images')
    if subfolder:
        images_dir = os.path.join(images_dir, subfolder)
    if iswindows:
        images_dir = os.path.normpath(images_dir)
    return images_dir


def get_library_uuid(db):
    try:
        library_uuid = db.library_id
    except:
        library_uuid = ''
    return library_uuid


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
    if unique_name is None:
        unique_name = menu_text
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
    
    if shortcut_name is None:
        shortcut_name = menu_text.replace('&','')
    
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
        if text is None:
            text = ''
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
        if (date_read == UNDEFINED_DATE) and default_to_today:
            date_read = now()
        if is_read_only:
            QTableWidgetItem.__init__(self, format_date(date_read, fmt))
            self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        else:
            QTableWidgetItem.__init__(self, '')
            dt = UNDEFINED_QDATETIME if date_read is None else QDateTime(date_read)
            self.setData(Qt.DisplayRole, dt)

class NoWheelComboBox(QComboBox):
    
    def wheelEvent (self, event):
        # Disable the mouse wheel on top of the combo box changing selection as plays havoc in a grid
        event.ignore()

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
        if icon:
            self.setIcon(icon)

class ReadOnlyLineEdit(QLineEdit):
    def __init__(self, text, parent):
        if text is None:
            text = ''
        QLineEdit.__init__(self, text, parent)
        self.setEnabled(False)

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
    def __init__(self, parent, values, selected_key=None, initial_items=None):
        QComboBox.__init__(self, parent)
        self.populate_combo(values, selected_key, initial_items)
    
    def populate_combo(self, values, selected_key=None, initial_items=None):
        self.clear()
        self.values = values
        if initial_items == None: initial_items = []
        
        selected_idx = start = 0
        for start, init in enumerate(initial_items, 1):
            self.addItem(init)
        
        for idx, (key, value) in enumerate(self.values.items(), start):
            self.addItem(value)
            if key == selected_key:
                selected_idx = idx
        
        self.setCurrentIndex(selected_idx)
    
    def selected_key(self):
        currentText = unicode(self.currentText()).strip()
        for key, value in self.values.items():
            if value == currentText:
                return key

class CustomColumnComboBox(QComboBox):
    def __init__(self, parent, custom_columns={}, selected_column='', initial_items=['']):
        QComboBox.__init__(self, parent)
        self.populate_combo(custom_columns, selected_column, initial_items)
    
    def populate_combo(self, custom_columns, selected_column='', initial_items=['']):
        self.clear()
        self.column_names = list()
        if initial_items == None: initial_items = []
        
        selected_idx = start = 0
        for start, init in enumerate(initial_items, 1):
            self.column_names.append('')
            self.addItem(init)
        
        for idx, (key, value) in enumerate(custom_columns.items(), start):
            self.column_names.append(key)
            self.addItem('{:s} ({:s})'.format(key, value.display_name))
            if key == selected_column:
                selected_idx = idx
        
        self.setCurrentIndex(selected_idx)
    
    def selected_column(self):
        return self.column_names[self.currentIndex()]

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


import re
# Simple Regex
class regex():
    
    def __init__(self, flag=None):
        
        #set the default flag
        self.flag = flag
        if self.flag == None:
            if PYTHON[0] == 2:
                self.flag = re.MULTILINE + re.DOTALL
            else:
                self.flag = re.ASCII + re.MULTILINE + re.DOTALL
                # calibre 5 // re.ASCII for Python3 only
            
    
    def match(self, pattern, string, flag=None):
        if flag == None: flag = self.flag
        return re.fullmatch(pattern, string, flag)
    
    def search(self, pattern, string, flag=None):
        if flag == None: flag = self.flag
        return re.search(pattern, string, flag)
    
    def searchall(self, pattern, string, flag=None):
        if flag == None: flag = self.flag
        if self.search(pattern, string, flag):
            return re.finditer(pattern, string, flag)
        else:
            return None
    
    def split(self, pattern, string, maxsplit=0, flag=None):
        if flag == None: flag = self.flag
        return re.split(pattern, string, maxsplit, flag)
    
    def simple(self, pattern, repl, string, flag=None):
        if flag == None: flag = self.flag
        return re.sub(pattern, repl, string, 0, flag)
    
    def loop(self, pattern, repl, string, flag=None):
        if flag == None: flag = self.flag
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

def CustomExceptionErrorDialog(parent, exception, custome_title=None, custome_msg=None, show=True):
    
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
        custome_msg = ''
    
    msg = custome_msg + '<b>{:s}</b>: '.format(exception.__class__.__name__) + prepare_string_for_xml(as_unicode(str(exception)))
    
    return error_dialog(parent, custome_title, msg, det_msg=fe, show=show, show_copy_button=True)



class PREFS_library(dict):
    '''
    Create a dictionary of preference stored in the library
    '''
    def __init__(self, key='settings', defaults={}):
        self._db = None
        self.key = key if key else ''
        self.defaults = defaults if defaults else {}
        
        if not isinstance(key, unicode) and not isinstance(key, str):
            raise TypeError("The 'key' for the namespaced preference is not a string")
            
        if not isinstance(defaults, dict):
            raise TypeError("The 'defaults' for the namespaced preference is not a dict")
        
        
        self._namespace = get__init__attribut('PREFS_NAMESPACE')
        
        self.refresh()
    
    @property
    def namespace(self):
        '''
        Defined a custom namespaced at the root of __init__.py // __init__.PREFS_NAMESPACE
        '''
        return self._namespace
    
    def __call__(self, prefs=None):
        if prefs is not None:
            self.set_in_library(prefs)
        else:
            self.refresh()
        return self
    
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
    
    def set(self, key, val):
        self.__setitem__(key, val)
    
    def __delitem__(self, key):
        self.refresh()
        try:
            dict.__delitem__(self, key)
        except KeyError:
            pass  # ignore missing keys
    
    def __enter__(self):
        self.refresh()
    
    def __exit__(self):
        self.set_in_library()
    
    def __str__(self):
        self.refresh()
        return dict.__str__(self._append_defaults(copy.copy(self)))
    
    
    def _append_defaults(self, prefs):
        for k, v in self.defaults.items():
            if k not in prefs:
                prefs[k] = v
        return prefs
    
    
    def refresh(self):
        if self._db != getattr(GUI, 'current_db', None):
            self._db = GUI.current_db
            self.clear()
            self.update(self.get_from_library())
    
    def get_from_library(self):
        rslt = self._db.prefs.get_namespaced(self.namespace, self.key, {})
        rslt = self._append_defaults(rslt)
        return rslt
    
    def set_in_library(self, prefs=None):
        self.refresh()
        if prefs is not None:
            self.clear()
            self.update(prefs)
        
        self._db.prefs.set_namespaced(self.namespace, self.key, self)
        self.refresh()


class CustomColumns():
    '''
    You should only need the following @staticmethod and @property of the CustomColumns:
    
    @staticmethod to retrieve the columns by type:
        get_names()
        get_tags()
        get_enumeration()
        get_float()
        get_datetime()
        get_rating()
        get_series()
        get_text()
        get_bool()
        get_comments()
        get_html()
        get_markdown()
        get_long_text()
        get_title()
        get_builded_text()
        get_builded_tag()
        get_from_name(name)
        get_all_custom_columns()
    
    @property string (read-only) to identify the CustomColumns instance
        name
        display_name
    
    @property bool (read-only) of CustomColumns instance
    that which identifies the type of the CustomColumns
        is_bool
        is_builded_tag
        is_builded_text
        is_comments
        is_composite
        is_datetime
        is_enumeration
        is_float
        is_integer
        is_names
        is_rating
        is_series
        is_tags
        is_text
        is_html
        is_long_text
        is_markdown
        is_title
        
    @property (read-only) of CustomColumns instance
    return is None if column does not support this element
        allow_half_stars = bool()
        category_sort = 'value'
        colnum = int()
        column = 'value'
        composite_contains_html = bool()
        composite_make_category = bool()
        composite_sort = string > one of then ['text', 'number', 'date', 'bool']
        composite_template = string()
        datatype = string()
        description = string()
        display = {} // contains an arbitrary data set. reanalys in other property
        enum_colors = string[]
        enum_values = string[]
        heading_position = string > one of then ['text', 'number', 'date', 'bool']
        is_category = bool()
        is_csp = False
        is_custom = True()
        is_editable = True
        is_multiple = {} // contains an arbitrary data set. reanalys in other property
        kind = 'field'
        label = string()
        link_column = 'value'
        names_split_regex_additional = string()
        rec_index = int()
        search_terms = []
        table = string()
        use_decorations = bool()
    '''
    _DB = None
    _STORED = {}
    
    _TYPES = [
        'is_names',
        'is_tags',
        
        'is_enumeration',
        'is_float',
        'is_integer',
        'is_datetime',
        'is_rating',
        'is_series',
        'is_text',
        'is_bool',
        
        'is_comments',
        'is_html',
        'is_markdown',
        'is_long_text',
        'is_title',
        
        'is_builded_text',
        'is_builded_tag',
    ]
    
    ## static method (public)
    
    @staticmethod
    def get_all_custom_columns():
        if CustomColumns._DB != getattr(GUI, 'current_db', None):
            CustomColumns._DB = GUI.current_db
            CustomColumns._STORED.clear()
            lst = []
            for k,v in GUI.library_view.model().custom_columns.items():
                lst.append(CustomColumns(k, v))
            
            CustomColumns._STORED = {cc.name:cc for cc in sorted(lst,key=CustomColumns._cmp)}
            
        return copy.copy(CustomColumns._STORED)
    
    @staticmethod
    def _get_columns_type(type_property):
        return {cc.name:cc for cc in CustomColumns.get_all_custom_columns().values() if getattr(cc, type_property, False)}
    
    @staticmethod
    def get_from_name(name):
        return CustomColumns.get_all_custom_columns().get(name, None)
    
    @staticmethod
    def get_names():
        return CustomColumns._get_columns_type('is_names')
    @staticmethod
    def get_tags():
        return CustomColumns._get_columns_type('is_tags')
    @staticmethod
    def get_enumeration():
        return CustomColumns._get_columns_type('is_enumeration')
    @staticmethod
    def get_float():
        return CustomColumns._get_columns_type('is_float')
    @staticmethod
    def get_datetime():
        return CustomColumns._get_columns_type('is_datetime')
    @staticmethod
    def get_rating():
        return CustomColumns._get_columns_type('is_rating')
    @staticmethod
    def get_series():
        return CustomColumns._get_columns_type('is_series')
    @staticmethod
    def get_text():
        return CustomColumns._get_columns_type('is_text')
    @staticmethod
    def get_bool():
        return CustomColumns._get_columns_type('is_bool')
    @staticmethod
    def get_comments():
        return CustomColumns._get_columns_type('is_comments')
    @staticmethod
    def get_html():
        return CustomColumns._get_columns_type('is_html')
    @staticmethod
    def get_markdown():
        return CustomColumns._get_columns_type('is_markdown')
    @staticmethod
    def get_long_text():
        return CustomColumns._get_columns_type('is_long_text')
    @staticmethod
    def get_title():
        return CustomColumns._get_columns_type('is_title')
    @staticmethod
    def get_builded_text():
        return CustomColumns._get_columns_type('is_builded_text')
    @staticmethod
    def get_builded_tag():
        return CustomColumns._get_columns_type('is_builded_tag')
    
    ## class method (internal)
    
    def __init__(self, name, src_dict):
        self._name = name
        self._src_dict = src_dict
    
    def __repr__ (self):
        #<calibre_plugins.epub_contributors_metadata.common_utils.CustomColumns instance at 0x1148C4B8>
        #''.join(['<', str(self.__class__), ' instance at ', hex(id(self)),'>'])
        return ''.join(['<"',self._name,'"', str(self._get_type()),'>'])
    
    def _get_property_dict(self, predicate=None):
        import inspect
        def _predicate(key, value):
            return True
        
        if not predicate:
            predicate = _predicate
        
        return dict(i for i in inspect.getmembers(self) if not inspect.ismethod(i[1]) and not inspect.isfunction(i[1]) and predicate(*i))
    
    def _get_type(self):
        def _predicate(key, value):
            return key in self._TYPES and value
        return self._get_property_dict(_predicate)
    
    def _cmp(self):
        return self.name.lower()
    
    @property
    def name(self):
        return self._name
    @property
    def display_name(self):
        return self._src_dict.get('name', None)
    @property
    def description(self):
        return self.display.get('description', None)
    
    @property
    def is_names(self):
        return self.datatype == 'text' and self.is_multiple and self.display.get('is_names', False)
    @property
    def is_tags(self):
        return self.datatype == 'text' and self.is_multiple and not self.display.get('is_names', False)
    
    @property
    def names_split_regex_additional(self):
        from calibre.utils.config import tweaks
        return tweaks['authors_split_regex']
    
    @property
    def is_text(self):
        return self.datatype == 'text' and not self.is_multiple
    @property
    def is_float(self):
        return self.datatype == 'float'
    @property
    def is_integer(self):
        return self.datatype == 'int'
    @property
    def is_datetime(self):
        return self.datatype == 'datetime'
    @property
    def is_rating(self):
        return self.datatype == 'rating'
    @property
    def is_series(self):
        return self.datatype == 'series'
    @property
    def is_bool(self):
        return self.datatype == 'bool'
    @property
    def is_enumeration(self):
        return self.datatype == 'enumeration'
    
    @property
    def enum_values(self):
        if self.is_enumeration:
            return self.display.get('enum_values', None)
        else:
            return None
    @property
    def enum_colors(self):
        if self.is_enumeration:
            return self.display.get('enum_colors', None)
        else:
            return None
    
    @property
    def is_comments(self):
        return self.datatype == 'comments'
    @property
    def is_html(self):
        return self.is_comments and self.display.get('interpret_as', None) == 'html'
    @property
    def is_markdown(self):
        return self.is_comments and self.display.get('interpret_as', None) == 'markdown'
    @property
    def is_title(self):
        return self.is_comments and self.display.get('interpret_as', None) == 'short-text'
    @property
    def is_long_text(self):
        return self.is_comments and self.display.get('interpret_as', None)== 'long-text'
    
    @property
    def heading_position(self):
        #"hide", "above", "side"
        if self.is_comments:
            return self.display.get('heading_position', None)
        else:
            return None
    
    @property
    def use_decorations(self):
        #"hide", "above", "side"
        if self.is_text or self.is_enumeration or self.is_builded_text:
            return self.display.get('use_decorations', None)
        else:
            return None
    @property
    def allow_half_stars(self):
        if self.is_rating:
            return self.display.get('allow_half_stars', None)
        else:
            return None
    
    
    @property
    def is_composite(self):
        return self.datatype == 'composite'
    @property
    def is_builded_text(self):
        return self.is_composite and self.is_multiple
    @property
    def is_builded_tag(self):
        return self.is_composite and not self.is_multiple
    
    @property
    def composite_sort(self):
        if self.is_composite:
            return self.display.get('composite_sort', None)
        else:
            return None
    @property
    def composite_make_category(self):
        if self.is_composite:
            return self.display.get('make_category', None)
        else:
            return None
    @property
    def composite_contains_html(self):
        if self.is_composite:
            return self.display.get('contains_html', None)
        else:
            return None
    @property
    def composite_template(self):
        if self.is_composite:
            return self.display.get('composite_template', None)
        else:
            return None
    
    
    @property
    def table(self):
        return self._src_dict.get('table', None)
    @property
    def column(self):
        return self._src_dict.get('column', None)
    @property
    def datatype(self):
        return self._src_dict.get('datatype', None)
    @property
    def kind(self):
        return self._src_dict.get('kind', None)
    @property
    def search_terms(self):
        return self._src_dict.get('search_terms', None)
    @property
    def label(self):
        return self._src_dict.get('label', None)
    @property
    def colnum(self):
        return self._src_dict.get('colnum', None)
    @property
    def display(self):
        return self._src_dict.get('display', None)
    @property
    def is_custom(self):
        return self._src_dict.get('is_custom', None)
    @property
    def is_category(self):
        return self._src_dict.get('is_category', None)
    @property
    def is_multiple(self):
        return self._src_dict.get('is_multiple', None)
    @property
    def link_column(self):
        return self._src_dict.get('link_column', None)
    @property
    def category_sort(self):
        return self._src_dict.get('category_sort', None)
    @property
    def rec_index(self):
        return self._src_dict.get('rec_index', None)
    @property
    def is_editable(self):
        return self._src_dict.get('is_editable', None)
    @property
    def is_csp(self):
        return self._src_dict.get('is_csp', None)
