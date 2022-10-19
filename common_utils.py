#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake <grant.drake@gmail.com> ; 2020, un_pogaz <un.pogaz@gmail.com>'
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

from calibre import prints
from calibre.constants import DEBUG, numeric_version as calibre_version
from calibre.gui2.ui import get_gui

PYTHON = sys.version_info

GUI = get_gui()

_PLUGIN = None
def get_plugin_attribut(name, default=None):
    """Retrieve a attribut on the main plugin class"""
    global _PLUGIN
    if not _PLUGIN:
        import importlib
        from calibre.customize import Plugin
        #Yes, it's very long for a one line. It's seems crazy, but it's fun and it works
        plugin_classes = [ obj for obj in itervalues(importlib.import_module('.'.join(__name__.split('.')[:-1])).__dict__) if isinstance(obj, type) and issubclass(obj, Plugin) and obj.name != 'Trivial Plugin' ]
        
        plugin_classes.sort(key=lambda c:(getattr(c, '__module__', None) or '').count('.'))
        _PLUGIN = plugin_classes[0]
    
    return getattr(_PLUGIN, name, default)

ROOT = __name__.split('.')[-2]

# Global definition of our plugin name. Used for common functions that require this.
PLUGIN_NAME = get_plugin_attribut('name', ROOT)
PREFS_NAMESPACE = get_plugin_attribut('PREFS_NAMESPACE', ROOT)
DEBUG_PRE = get_plugin_attribut('DEBUG_PRE', PLUGIN_NAME)

BASE_TIME = time.time()
def debug_print(*args):
    if DEBUG:
        prints('DEBUG', DEBUG_PRE+':', *args)
        #prints('DEBUG', DEBUG_PRE,'({:.3f})'.format(time.time()-BASE_TIME),':', *args)


# ----------------------------------------------
#          Icon Management functions
# ----------------------------------------------
def __Icon_Management__(): pass

try:
    from qt.core import QIcon, QPixmap, QApplication
except ImportError:
    from PyQt5.Qt import QIcon, QPixmap, QApplication

from calibre.constants import iswindows
from calibre.constants import numeric_version as calibre_version
from calibre.utils.config import config_dir

# Global definition of our plugin resources. Used to share between the xxxAction and xxxBase
# classes if you need any zip images to be displayed on the configuration dialog.
PLUGIN_RESOURCES = {}

THEME_COLOR = ['', 'dark', 'light']

def get_theme_color():
    """Get the theme color of Calibre"""
    if calibre_version > (5, 90):
        return THEME_COLOR[1] if QApplication.instance().is_dark_theme else THEME_COLOR[2]
    return THEME_COLOR[0]

def get_icon_themed(icon_name, theme_color=None):
    """Apply the theme color to a path"""
    theme_color = get_theme_color() if theme_color is None else theme_color
    return icon_name.replace('/', '/'+theme_color+'/', 1).replace('//', '/')

def load_plugin_resources(plugin_path, names=[]):
    """
    Load all images in the plugin and the additional specified name.
    Set our global store of plugin name and icon resources for sharing between
    the InterfaceAction class which reads them and the ConfigWidget
    if needed for use on the customization dialog for this plugin.
    """
    from calibre.utils.zipfile import ZipFile
    
    global PLUGIN_RESOURCES
    
    if plugin_path is None:
        raise ValueError('This plugin was not loaded from a ZIP file')
    
    names = names or []
    ans = {}
    with ZipFile(plugin_path, 'r') as zf:
        for entry in zf.namelist():
            if entry in names or (entry.startswith('images/') and os.path.splitext(entry)[1].lower() == '.png' and entry not in PLUGIN_RESOURCES):
                ans[entry] = zf.read(entry)
    
    PLUGIN_RESOURCES.update(ans)

def get_icon(icon_name):
    """
    Retrieve a QIcon for the named image from the zip file if it exists,
    or if not then from Calibre's image cache.
    """
    def themed_icon(icon_name):
        if calibre_version < (6,0,0):
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
    """
    Retrieve a QPixmap for the named image
    Any icons belonging to the plugin must be prefixed with 'images/'
    """
    
    if not icon_name.startswith('images/'):
        # We know this is definitely not an icon belonging to this plugin
        pixmap = QPixmap()
        pixmap.load(I(icon_name))
        return pixmap
    
    # Build the icon_name according to the theme of the OS or Qt
    icon_themed = get_icon_themed(icon_name)
    
    if PLUGIN_NAME:
        # Check to see whether the icon exists as a Calibre resource
        # This will enable skinning if the user stores icons within a folder like:
        # ...\AppData\Roaming\calibre\resources\images\Plugin_Name\
        def get_from_local(name):
            local_images_dir = get_local_resource('images', PLUGIN_NAME)
            local_image_path = os.path.join(local_images_dir, name.replace('images/', ''))
            if os.path.exists(local_image_path):
                pxm = QPixmap()
                pxm.load(local_image_path)
                return pxm
            return None
        
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
    
    return pixmap

def get_local_resource(*subfolder):
    """
    Returns a path to the user's local resources folder
    If a subfolder name parameter is specified, appends this to the path
    """
    rslt = os.path.join(config_dir, 'resources', *[f.replace('/','-').replace('\\','-') for f in subfolder])
    
    if iswindows:
        rslt = os.path.normpath(rslt)
    return rslt


# ----------------------------------------------
#                Library functions
# ----------------------------------------------
def __Library__(): pass

from calibre.gui2 import error_dialog

def no_launch_error(title, name=None, msg=None):
    """Show a error dialog  for an operation that cannot be launched"""
    
    if msg and len(msg) > 0:
        msg = '\n'+msg
    else:
        msg = ''
    
    error_dialog(GUI, title, (title +'.\n'+ _('Could not to launch {:s}').format(PLUGIN_NAME or name) + msg), show=True, show_copy_button=False)

def _BookIds_error(book_ids, show_error, title, name=None):
    if not book_ids and show_error:
        no_launch_error(title, name=name)
    return book_ids

def get_BookIds_selected(show_error=False):
    """return the books id selected in the gui"""
    rows = GUI.library_view.selectionModel().selectedRows()
    if not rows or len(rows) == 0:
        ids = []
    else:
        ids = GUI.library_view.get_selected_ids()
   
    return _BookIds_error(ids, show_error, _('No book selected'))

def get_BookIds_all(show_error=False):
    """return all books id in the library"""
    ids = GUI.current_db.all_ids()
    return _BookIds_error(ids, show_error, _('No book in the library'))

def get_BookIds_virtual(show_error=False):
    """return the books id of the virtual library (without search restriction)"""
    ids = get_BookIds('', use_search_restriction=False, use_virtual_library=True)
    return _BookIds_error(ids, show_error, _('No book in the virtual library'))

def get_BookIds_filtered(show_error=False):
    """return the books id of the virtual library AND search restriction applied.
    This is the strictest result"""
    ids = get_BookIds('', use_search_restriction=True, use_virtual_library=True)
    return _BookIds_error(ids, show_error, _('No book in the virtual library'))

def get_BookIds_search(show_error=False):
    """return the books id of the current search"""
    ids = get_BookIds(get_last_search(), use_search_restriction=True, use_virtual_library=True)
    return _BookIds_error(ids, show_error, _('No book in the current search'))

def get_BookIds(query, use_search_restriction=True, use_virtual_library=True):
    """
    return the books id corresponding to the query
    
    query:
        Search query of wanted books
    
    use_search_restriction:
        Limit the search to the actual search restriction
    
    use_virtual_library:
        Limit the search to the actual virtual library
    """
    data = GUI.current_db.data
    query = query or ''
    search_restriction = data.search_restriction if use_search_restriction else ''
    return data.search_getting_ids(query, search_restriction,
                                    set_restriction_count=False, use_virtual_library=use_virtual_library, sort_results=True)


def get_curent_search():
    """Get the current search string. Can be invalid"""
    return GUI.search.current_text

def get_last_search():
    """Get last search string performed with succes"""
    return GUI.library_view.model().last_search

def get_curent_virtual():
    """The virtual library, can't be a temporary VL"""
    data = GUI.current_db.data
    return data.get_base_restriction_name(), data.get_base_restriction()

def get_curent_restriction_search():
    """The search restriction is a top level filtre, based on the saved searches"""
    data = GUI.current_db.data
    name = data.get_search_restriction_name()
    return name, get_saved_searches().get(name, data.search_restriction)

def get_virtual_libraries():
    """Get all virtual library set in the database"""
    return GUI.current_db.prefs.get('virtual_libraries', {})

def get_saved_searches():
    """Get all saved searches set in the database"""
    return GUI.current_db.prefs.get('saved_searches', {})


def get_marked(label=None):
    """
    Get the marked books
    
    label:
        Filtre to only label. No case sensitive
    
    return: { label : [id,] }
    """
    
    rslt = {}
    for k,v in iteritems(GUI.current_db.data.marked_ids):
        v = str(v).lower()
        if v not in rslt:
            rslt[v] = [k]
        else:
            rslt[v].append(k)
    
    if label == None:
        return rslt
    else:
        label = str(label).lower()
        return { label:rslt[label] }

def set_marked(label, book_ids, append=False, reset=False):
    """
    Set the marked books
    
    label:
        String label. No case sensitive
    
    book_ids:
        Book id to affect the label
    
    append:
        Append the book id to the books that already this label.
        By default clear the previous book with this lable.
    
    book_ids:
        Book id to affect the label
    """
    label = str(label).lower()
    marked = {} if reset else GUI.current_db.data.marked_ids.copy()
    
    if not append:
        del_id = []
        for k,v in iteritems(marked):
            if v == label: del_id.append(k)
        
        for k in del_id:
            del marked[k]
    
    marked.update( {idx:label for idx in book_ids} )
    GUI.current_db.data.set_marked_ids(marked)


# ----------------------------------------------
#                Menu functions
# ----------------------------------------------
def __Menu__(): pass

from calibre.gui2.actions import menu_action_unique_name

# Global definition of our menu actions. Used to ensure we can cleanly unregister
# keyboard shortcuts when rebuilding our menus.
plugin_menu_actions = []

def unregister_menu_actions():
    """
    For plugins that dynamically rebuild their menus, we need to ensure that any
    keyboard shortcuts are unregistered for them each time.
    Make sure to call this before .clear() of the menu items.
    """
    global plugin_menu_actions
    for action in plugin_menu_actions:
        if hasattr(action, 'calibre_shortcut_unique_name'):
            GUI.keyboard.unregister_shortcut(action.calibre_shortcut_unique_name)
        # starting in calibre 2.10.0, actions are registers at
        # the top gui level for OSX' benefit.
        if calibre_version >= (2,10,0):
            GUI.removeAction(action)
    plugin_menu_actions = []

def create_menu_action_unique(ia, parent_menu, menu_text, image=None, tooltip=None,
                       shortcut=None, triggered=None, is_checked=None, shortcut_name=None,
                       unique_name=None, favourites_menu_unique_name=None):
    """
    Create a menu action with the specified criteria and action, using the new
    InterfaceAction.create_menu_action() function which ensures that regardless of
    whether a shortcut is specified it will appear in Preferences->Keyboard
    
    For a full description of the parameters, see: calibre\gui2\actions\__init__.py
    """
    orig_shortcut = shortcut
    kb = ia.gui.keyboard
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
    
    if shortcut_name is None:
        shortcut_name = menu_text.replace('&','')
    
    if calibre_version >= (5,4,0):
        # The persist_shortcut parameter only added from 5.4.0 onwards.
        # Used so that shortcuts specific to other libraries aren't discarded.
        ac = ia.create_menu_action(parent_menu, unique_name, menu_text, icon=None,
                                   shortcut=shortcut, description=tooltip,
                                   triggered=triggered, shortcut_name=shortcut_name,
                                   persist_shortcut=True)
    else:
        ac = ia.create_menu_action(parent_menu, unique_name, menu_text, icon=None,
                                   shortcut=shortcut, description=tooltip,
                                   triggered=triggered, shortcut_name=shortcut_name)
    if shortcut == False and not orig_shortcut == False:
        if ac.calibre_shortcut_unique_name in ia.gui.keyboard.shortcuts:
            kb.replace_action(ac.calibre_shortcut_unique_name, ac)
    if image:
        ac.setIcon(get_icon(image))
    if is_checked is not None:
        ac.setCheckable(True)
        if is_checked:
            ac.setChecked(True)
    # For use by the Favourites Menu plugin. If this menu action has text
    # that is not constant through the life of this plugin, then we need
    # to attribute it with something that will be constant that the
    # Favourites Menu plugin can use to identify it.
    if favourites_menu_unique_name:
        ac.favourites_menu_unique_name = favourites_menu_unique_name
    
    # Append to our list of actions for this plugin to unregister when menu rebuilt
    global plugin_menu_actions
    plugin_menu_actions.append(ac)
    
    return ac

def create_menu_item(ia, parent_menu, menu_text, image=None, tooltip=None,
                     shortcut=(), triggered=None, is_checked=None):
    """
    Create a menu action with the specified criteria and action
    Note that if no shortcut is specified, will not appear in Preferences->Keyboard
    This method should only be used for actions which either have no shortcuts,
    or register their menus only once. Use create_menu_action_unique for all else.

    Currently this function is only used by open_with and search_the_internet plugins
    and would like to investigate one day if it can be removed from them.
    """
    if shortcut is not None:
        if len(shortcut) == 0:
            shortcut = ()
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
    
    # Append to our list of actions for this plugin to unregister when menu rebuilt
    global plugin_menu_actions
    plugin_menu_actions.append(ac)
    
    return ac

# ----------------------------------------------
#               Functions
# ----------------------------------------------
def __Functions__(): pass

def get_date_format(tweak_name='gui_timestamp_display_format', default_fmt='dd MMM yyyy'):
    from calibre.utils.config import tweaks
    format = tweaks[tweak_name]
    if format is None:
        format = default_fmt
    return format

# ----------------------------------------------
#               Widgets
# ----------------------------------------------
def __Widgets__(): pass

try:
    from qt.core import (Qt, QTableWidgetItem, QComboBox, QHBoxLayout, QLabel, QFont, 
                        QDateTime, QStyledItemDelegate, QLineEdit)
except ImportError:
    from PyQt5.Qt import (Qt, QTableWidgetItem, QComboBox, QHBoxLayout, QLabel, QFont, 
                        QDateTime, QStyledItemDelegate, QLineEdit)

from calibre.gui2 import error_dialog, UNDEFINED_QDATETIME
from calibre.utils.date import now, format_date, UNDEFINED_DATE
from calibre.gui2.library.delegates import DateDelegate as _DateDelegate

class ImageTitleLayout(QHBoxLayout):
    """
    A reusable layout widget displaying an image followed by a title
    """
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

class CheckableTableWidgetItem(QTableWidgetItem):
    """
    For use in a table cell, displays a checkbox that can potentially be tristate
    """
    def __init__(self, checked=False, is_tristate=False):
        QTableWidgetItem.__init__(self, '')
        self.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled )
        if is_tristate:
            self.setFlags(self.flags() | Qt.ItemFlag.ItemIsUserTristate)
        if checked:
            self.setCheckState(Qt.Checked)
        else:
            if is_tristate and checked is None:
                self.setCheckState(Qt.CheckState.PartiallyChecked)
            else:
                self.setCheckState(Qt.CheckState.Unchecked)
    
    def get_boolean_value(self):
        """
        Return a boolean value indicating whether checkbox is checked
        If this is a tristate checkbox, a partially checked value is returned as None
        """
        if self.checkState() == Qt.PartiallyChecked:
            return None
        else:
            return self.checkState() == Qt.Checked

class DateDelegate(_DateDelegate):
    """
    Delegate for dates. Because this delegate stores the
    format as an instance variable, a new instance must be created for each
    column. This differs from all the other delegates.
    """
    def __init__(self, parent, fmt='dd MMM yyyy', default_to_today=True):
        DateDelegate.__init__(self, parent)
        self.format = get_date_format(default_fmt=fmt)
        self.default_to_today = default_to_today
        print('DateDelegate fmt:',fmt)

    def createEditor(self, parent, option, index):
        qde = QStyledItemDelegate.createEditor(self, parent, option, index)
        qde.setDisplayFormat(self.format)
        qde.setMinimumDateTime(UNDEFINED_QDATETIME)
        qde.setSpecialValueText(_('Undefined'))
        qde.setCalendarPopup(True)
        return qde

    def setEditorData(self, editor, index):
        val = index.model().data(index, Qt.DisplayRole)
        print('setEditorData val:',val)
        if val is None or val == UNDEFINED_QDATETIME:
            if self.default_to_today:
                val = self.default_date
            else:
                val = UNDEFINED_QDATETIME
        editor.setDateTime(val)

    def setModelData(self, editor, model, index):
        val = editor.dateTime()
        print('setModelData: ',val)
        if val <= UNDEFINED_QDATETIME:
            model.setData(index, UNDEFINED_QDATETIME, Qt.EditRole)
        else:
            model.setData(index, QDateTime(val), Qt.EditRole)

class DateTableWidgetItem(QTableWidgetItem):
    def __init__(self, date_read, is_read_only=False, default_to_today=False, fmt=None):
        if date_read is None or date_read == UNDEFINED_DATE and default_to_today:
            date_read = now()
        if is_read_only:
            QTableWidgetItem.__init__(self, format_date(date_read, fmt))
            self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        else:
            QTableWidgetItem.__init__(self, '')
            self.setData(Qt.DisplayRole, QDateTime(date_read))

class RatingTableWidgetItem(QTableWidgetItem):
    def __init__(self, rating, is_read_only=False):
        QTableWidgetItem.__init__(self, '')
        self.setData(Qt.DisplayRole, rating)
        if is_read_only:
            self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)

class TextIconWidgetItem(QTableWidgetItem):
    def __init__(self, text, icon, tooltip=None, is_read_only=False):
        QTableWidgetItem.__init__(self, text)
        if icon: self.setIcon(icon)
        if tooltip: self.setToolTip(tooltip)
        if is_read_only: self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)

class ReadOnlyTableWidgetItem(QTableWidgetItem):
    """
    For use in a table cell, displays text the user cannot select or modify.
    """
    def __init__(self, text):
        text = text or ''
        QTableWidgetItem.__init__(self, text)
        self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)

class ReadOnlyCheckableTableWidgetItem(ReadOnlyTableWidgetItem):
    '''
    For use in a table cell, displays a checkbox next to some text the user cannot select or modify.
    '''
    def __init__(self, text, checked=False, is_tristate=False):
        ReadOnlyCheckableTableWidgetItem.__init__(self, text)
        try: # For Qt Backwards compatibility.
            self.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled )
        except:
            self.setFlags(Qt.ItemFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled ))
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

class ReadOnlyTextIconWidgetItem(ReadOnlyTableWidgetItem):
    """
    For use in a table cell, displays an icon the user cannot select or modify.
    """
    def __init__(self, text, icon):
        ReadOnlyTableWidgetItem.__init__(self, text)
        if icon: self.setIcon(icon)

# ----------------------------------------------
#               Controls
# ----------------------------------------------
def __Controls__(): pass

class ReadOnlyLineEdit(QLineEdit):
    def __init__(self, text, parent):
        text = text or ''
        QLineEdit.__init__(self, text, parent)
        self.setEnabled(False)

class NoWheelComboBox(QComboBox):
    """
    For combobox displayed in a table cell using the mouse wheel has nasty interactions
    due to the conflict between scrolling the table vs scrolling the combobox item.
    Inherit from this class to disable the combobox changing value with mouse wheel.
    """
    def wheelEvent(self, event):
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
        self.currentTextChanged.connect(self.current_text_changed)
    
    def populate_combo(self, custom_columns, selected_column='', initial_items=['']):
        self.clear()
        self.custom_columns = custom_columns
        self.column_names = []
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
    
    def refresh_ToolTip(self):
        cc = self.custom_columns.get(self.get_selected_column(), None)
        if cc:
            self.setToolTip(cc.description)
        else:
            self.setToolTip('')
    
    def get_selected_column(self):
        return self.column_names[self.currentIndex()]
    
    def current_text_changed(self, new_text):
        self.refresh_ToolTip()
        self.current_index = self.currentIndex()

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
    """
    Unfortunately there is a flaw in the Qt implementation which means that
    when the QComboBox is in editable mode that dropEvent is not fired
    if you drag into the editable text area. Working around this by having
    a custom LineEdit() set for the parent combobox.
    """
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
    """
    Unfortunately there is a flaw in the Qt implementation which means that
    when the QComboBox is in editable mode that dropEvent is not fired
    if you drag into the editable text area. Working around this by having
    a custom LineEdit() set for the parent combobox.
    """
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


# ----------------------------------------------
#               Dialog functions
# ----------------------------------------------
def __Dialog__(): pass

try:
    from qt.core import (QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, 
                        QListWidget, QProgressBar, QAbstractItemView, QTextEdit, 
                        QApplication, Qt, QTextBrowser, QSize, QLabel)
except ImportError:
    from PyQt5.Qt import (QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, 
                        QListWidget, QProgressBar, QAbstractItemView, QTextEdit, 
                        QApplication, Qt, QTextBrowser, QSize, QLabel)

from calibre.gui2 import gprefs, Application
from calibre.gui2.keyboard import ShortcutConfig

class SizePersistedDialog(QDialog):
    """
    This dialog is a base class for any dialogs that want their size/position
    restored when they are next opened.
    """
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
        """
        Invoked when the dialog is closing. Override this function to call
        save_custom_pref() if you have a setting you want persisted that you can
        retrieve in your __init__() using load_custom_pref() when next opened
        """
        pass
    
    def load_custom_pref(self, name, default=None):
        return gprefs.get(self.unique_pref_name+':'+name, default)
    
    def save_custom_pref(self, name, value):
        gprefs[self.unique_pref_name+':'+name] = value
    
    def help_link_activated(self, url):
        if self.plugin_action is not None:
            self.plugin_action.show_help(anchor=self.help_anchor)

class KeyboardConfigDialog(SizePersistedDialog):
    """
    This dialog is used to allow editing of keyboard shortcuts.
    """
    def __init__(self, gui, group_name):
        SizePersistedDialog.__init__(self, gui, 'Keyboard shortcut dialog')
        self.gui = gui
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
        self.keyboard_widget.initialize(self.gui.keyboard)
        self.keyboard_widget.highlight_group(self.group_name)
    
    def commit(self):
        self.keyboard_widget.commit()
        self.accept()

def edit_keyboard_shortcuts(plugin_action):
    getattr(plugin_action, 'rebuild_menus', ())()
    d = KeyboardConfigDialog(GUI, plugin_action.action_spec[0])
    if d.exec_() == d.Accepted:
        GUI.keyboard.finalize()

class PrefsViewerDialog(SizePersistedDialog):
    def __init__(self, gui, namespace):
        SizePersistedDialog.__init__(self, gui, 'Prefs Viewer dialog')
        self.setWindowTitle(_('Preferences for:')+' '+namespace)
        
        self.gui = gui
        self.db = GUI.current_db
        self.namespace = namespace
        self.prefs = {}
        self.current_key = None
        self._init_controls()
        self.resize_dialog()
        
        self._populate_settings()
        
        if self.keys_list.count():
            self.keys_list.setCurrentRow(0)
    
    def _init_controls(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        
        ml = QHBoxLayout()
        layout.addLayout(ml, 1)
        
        self.keys_list = QListWidget(self)
        self.keys_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.keys_list.setFixedWidth(150)
        self.keys_list.setAlternatingRowColors(True)
        ml.addWidget(self.keys_list)
        self.value_text = QTextEdit(self)
        self.value_text.setReadOnly(False)
        ml.addWidget(self.value_text, 1)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._apply_changes)
        button_box.rejected.connect(self.reject)
        self.clear_button = button_box.addButton(_('Clear'), QDialogButtonBox.ResetRole)
        self.clear_button.setIcon(get_icon('trash.png'))
        self.clear_button.setToolTip(_('Clear all settings for this plugin'))
        self.clear_button.clicked.connect(self._clear_settings)
        layout.addWidget(button_box)
    
    def _populate_settings(self):
        self.prefs.clear()
        self.keys_list.clear()
        ns_prefix = 'namespaced:{:s}:'.format(self.namespace)
        ns_len = len(ns_prefix)
        for key in sorted([k[ns_len:] for k in self.db.prefs.keys() if k.startswith(ns_prefix)]):
            self.keys_list.addItem(key)
            val = self.db.prefs.get_namespaced(self.namespace, key, None)
            self.prefs[key] = self.db.prefs.to_raw(val) if val != None else None
        self.keys_list.setMinimumWidth(self.keys_list.sizeHintForColumn(0))
        self.keys_list.currentRowChanged[int].connect(self._current_row_changed)
    
    def _save_current_row(self):
        if self.current_key != None:
            self.prefs[self.current_key] = unicode(self.value_text.toPlainText())
    
    def _current_row_changed(self, new_row):
        self._save_current_row()
        
        if new_row < 0:
            self.value_text.clear()
            self.current_key = None
            return
        
        self.current_key = unicode(self.keys_list.currentItem().text())
        self.value_text.setPlainText(self.prefs[self.current_key])
    
    def _apply_changes(self):
        self._save_current_row()
        for k,v in iteritems(self.prefs):
            try:
                self.db.prefs.raw_to_object(v)
            except Exception as ex:
                CustomExceptionErrorDialog(ex, custome_msg=_('The changes cannot be applied.'))
                return
        
        from calibre.gui2.dialogs.confirm_delete import confirm
        message = '<p>'+_('Are you sure you want to change your settings in this library for this plugin?')+'</p>' \
                  '<p>'+_('Any settings in other libraries or stored in a JSON file in your calibre plugins ' \
                  'folder will not be touched.')+'</p>'
        if not confirm(message, self.namespace+'_apply_settings', self):
            return
        
        for k,v in iteritems(self.prefs):
            self.db.prefs.set_namespaced(self.namespace, k, self.db.prefs.raw_to_object(v))
        self.close()
    
    def _clear_settings(self):
        from calibre.gui2.dialogs.confirm_delete import confirm
        message = '<p>'+_('Are you sure you want to clear your settings in this library for this plugin?')+'</p>' \
                  '<p>'+_('Any settings in other libraries or stored in a JSON file in your calibre plugins ' \
                  'folder will not be touched.')+'</p>'
        if not confirm(message, self.namespace+'_clear_settings', self):
            return
        
        for k in self.prefs.keys():
            self.prefs[k] = '{}'
            self.db.prefs.set_namespaced(self.namespace, k, self.db.prefs.raw_to_object('{}'))
        self._populate_settings()
        self.close()

def view_library_prefs():
    GUI.current_db
    d = PrefsViewerDialog(GUI, PREFS_NAMESPACE)
    d.exec_()

class ProgressBarDialog(QDialog):
    def __init__(self, parent=None, max_items=100, window_title='Progress Bar',
                 label='Label goes here', on_top=False):
        if on_top:
            ProgressBarDialog.__init__(self, parent=parent, flags=Qt.WindowStaysOnTopHint)
        else:
            ProgressBarDialog.__init__(self, parent=parent)
        self.application = Application
        self.setWindowTitle(window_title)
        self.l = QVBoxLayout(self)
        self.setLayout(self.l)
        
        self.label = QLabel(label)
        #self.label.setAlignment(Qt.AlignHCenter)
        self.l.addWidget(self.label)
        
        self.progressBar = QProgressBar(self)
        self.progressBar.setRange(0, max_items)
        self.progressBar.setValue(0)
        self.l.addWidget(self.progressBar)
    
    def increment(self):
        self.progressBar.setValue(self.progressBar.value() + 1)
        self.refresh()
    
    def refresh(self):
        self.application.processEvents()
    
    def set_label(self, value):
        self.label.setText(value)
        self.refresh()
    
    def left_align_label(self):
        self.label.setAlignment(Qt.AlignLeft )
    
    def set_maximum(self, value):
        self.progressBar.setMaximum(value)
        self.refresh()
    
    def set_value(self, value):
        self.progressBar.setValue(value)
        self.refresh()
    
    def set_progress_format(self, progress_format=None):
        pass

class ViewLogDialog(QDialog):
    def __init__(self, title, html, parent=None):
        QDialog.__init__(self, parent)
        self.l = l = QVBoxLayout()
        self.setLayout(l)
        
        self.tb = QTextBrowser(self)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        # Rather than formatting the text in <pre> blocks like the calibre
        # ViewLog does, instead just format it inside divs to keep style formatting
        html = html.replace('\t','&nbsp;&nbsp;&nbsp;&nbsp;').replace('\n', '<br/>')
        html = html.replace('> ','>&nbsp;')
        self.tb.setHtml('<div>{:s}</div>'.format(html))
        QApplication.restoreOverrideCursor()
        l.addWidget(self.tb)
        
        self.bb = QDialogButtonBox(QDialogButtonBox.Ok)
        self.bb.accepted.connect(self.accept)
        self.bb.rejected.connect(self.reject)
        self.copy_button = self.bb.addButton(_('Copy to clipboard'),
                self.bb.ActionRole)
        self.copy_button.setIcon(get_icon('edit-copy.png'))
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        l.addWidget(self.bb)
        self.setModal(False)
        self.resize(QSize(700, 500))
        self.setWindowTitle(title)
        self.setWindowIcon(get_icon('debug.png'))
        self.show()
    
    def copy_to_clipboard(self):
        txt = self.tb.toPlainText()
        QApplication.clipboard().setText(txt)


# ----------------------------------------------
#               Ohters
# ----------------------------------------------
def __Ohters__(): pass

from calibre.gui2 import error_dialog, show_restart_warning
from calibre.utils.config import JSONConfig, DynamicConfig

def current_db():
    """Safely provides the current_db or None"""
    return getattr(get_gui(),'current_db', None)
    # db.library_id

def has_restart_pending(show_warning=True, msg_warning=None):
    restart_pending = GUI.must_restart_before_config
    if restart_pending and show_warning:
        msg = msg_warning if msg_warning else _('You cannot configure this plugin before calibre is restarted.')
        if show_restart_warning(msg):
            GUI.quit(restart=True)
    return restart_pending


def duplicate_entry(lst):
    return list(set([x for x in lst if lst.count(x) > 1]))

# Simple Regex
class regex():
    
    import re as _re
    def __init__(self, flag=None):
        
        #set the default flag
        self.flag = flag
        if not self.flag:
            if PYTHON[0] == 2:
                self.flag = regex._re.MULTILINE + regex._re.DOTALL
            else:
                self.flag = regex._re.ASCII + regex._re.MULTILINE + regex._re.DOTALL
                # calibre 5 // re.ASCII for Python3 only
            
    
    def __call__(self, flag=None):
        return self.__class__(flag)
    
    def match(self, pattern, string, flag=None):
        flag = flag or self.flag
        return regex._re.fullmatch(pattern, string, flag)
    
    def search(self, pattern, string, flag=None):
        flag = flag or self.flag
        return regex._re.search(pattern, string, flag)
    
    def searchall(self, pattern, string, flag=None):
        flag = flag or self.flag
        if self.search(pattern, string, flag):
            return regex._re.finditer(pattern, string, flag)
        else:
            return None
    
    def split(self, pattern, string, maxsplit=0, flag=None):
        flag = flag or self.flag
        return regex._re.split(pattern, string, maxsplit, flag)
    
    def simple(self, pattern, repl, string, flag=None):
        flag = flag or self.flag
        return regex._re.sub(pattern, repl, string, 0, flag)
    
    def loop(self, pattern, repl, string, flag=None):
        flag = flag or self.flag
        i = 0
        while self.search(pattern, string, flag):
            if i > 1000:
                raise regex.Exception('the pattern and substitution string caused an infinite loop', pattern, repl)
            string = self.simple(pattern, repl, string, flag)
            i+=1
            
        return string
    
    class Exception(BaseException):
        def __init__(self, msg, pattern=None, repl=None):
            self.pattern = pattern
            self.repl = repl
            self.msg = msg
        
        def __str__(self):
            return self.msg
regex = regex()
"""Easy Regex"""


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
    
    msg = []
    msg.append('<span>' + prepare_string_for_xml(as_unicode(_('The {:s} plugin has encounter a unhandled exception.').format(PLUGIN_NAME))))
    if custome_msg: msg.append(custome_msg)
    msg.append('<b>{:s}</b>: '.format(exception.__class__.__name__) + prepare_string_for_xml(as_unicode(str(exception))))
    
    return error_dialog(GUI, custome_title, '\n'.join(msg).replace('\n', '<br>'), det_msg=fe, show=show, show_copy_button=True)


class PREFS_json(JSONConfig):
    """
    Use plugin name to create a JSONConfig file
    to store the preferences for plugin
    """
    def __init__(self):
        JSONConfig.__init__(self, 'plugins/'+PLUGIN_NAME)
    
    def update(self, other, **kvargs):
        JSONConfig.update(self, other, **kvargs)
        self.commit()
    
    def __call__(self):
        self.refresh()
        return self
    
    def deepcopy_dict(self):
        """
        get a deepcopy dict of this instance
        """
        rslt = {}
        for k,v in iteritems(self):
            rslt[copy.deepcopy(k)] = copy.deepcopy(v)
        
        for k, v in iteritems(self.defaults):
            if k not in rslt:
                rslt[k] = copy.deepcopy(v)
        return rslt

class PREFS_dynamic(DynamicConfig):
    """
    Use plugin name to create a DynamicConfig file
    to store the preferences for plugin
    """
    def __init__(self):
        self._no_commit = False
        DynamicConfig.__init__(self, 'plugins/'+PLUGIN_NAME)
    
    def commit(self):
        if self._no_commit:
            return
        DynamicConfig.commit(self)
    
    def __enter__(self):
        self._no_commit = True

    def __exit__(self, *args):
        self._no_commit = False
        self.commit()
    
    def __call__(self):
        self.refresh()
        return self
    
    def update(self, other, **kvargs):
        DynamicConfig.update(self, other, **kvargs)
        self.commit()
    
    def deepcopy_dict(self):
        """
        get a deepcopy dict of this instance
        """
        rslt = {}
        for k,v in iteritems(self):
            rslt[copy.deepcopy(k)] = copy.deepcopy(v)
        
        for k, v in iteritems(self.defaults):
            if k not in rslt:
                rslt[k] = copy.deepcopy(v)
        return rslt

class PREFS_library(dict):
    """
    Create a dictionary of preference stored in the library
    
    Defined a custom namespaced at the root of __init__.py // __init__.PREFS_NAMESPACE
    """
    def __init__(self, key='settings', defaults={}):
        self._no_commit = False
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
    
    def _check_db(self):
        new_db = current_db()
        if new_db and self._db != new_db:
            self._db = new_db
        return self._db != None
    
    def refresh(self):
        if self._check_db():
            rslt = self._db.prefs.get_namespaced(self.namespace, self.key, {})
            self._no_commit = True
            self.clear()
            self.update(rslt)
            self._no_commit = False
    
    def commit(self):
        if self._no_commit:
            return
        
        if self._check_db():
            self._db.prefs.set_namespaced(self.namespace, self.key, self.deepcopy_dict())
            self.refresh()
    
    def __enter__(self):
        self.refresh()
        self._no_commit = True
    
    def __exit__(self, *args):
        self._no_commit = False
        self.commit()
    
    def __call__(self):
        self.refresh()
        return self
    
    def update(self, other, **kvargs):
        dict.update(self, other, **kvargs)
        self.commit()
    
    def deepcopy_dict(self):
        """
        get a deepcopy dict of this instance
        """
        rslt = {}
        for k,v in iteritems(self):
            rslt[copy.deepcopy(k)] = copy.deepcopy(v)
        
        for k, v in iteritems(self.defaults):
            if k not in rslt:
                rslt[k] = copy.deepcopy(v)
        return rslt
