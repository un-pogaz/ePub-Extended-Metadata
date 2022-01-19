#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'
__docformat__ = 'restructuredtext en'

import os, time, copy
# calibre Python 3 compatibility.
from six import text_type as unicode

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from functools import partial
from datetime import datetime
from collections import defaultdict

try:
    from qt.core import QToolButton, QMenu, QProgressDialog, QTimer, QSize
except ImportError:
    from PyQt5.Qt import QToolButton, QMenu, QProgressDialog, QTimer, QSize

from calibre import prints
from calibre.constants import numeric_version as calibre_version
from calibre.gui2 import error_dialog, warning_dialog, question_dialog, info_dialog
from calibre.gui2.actions import InterfaceAction
from polyglot.builtins import iteritems

from calibre_plugins.epub_contributors_metadata.config import ICON, PREFSclass, KEY, KEY_EXCLUDE_OPTION, KEY_EXCLUDE_INVALIDE
from calibre_plugins.epub_contributors_metadata.common_utils import set_plugin_icon_resources, get_icon, create_menu_action_unique, create_menu_item, debug_print, CustomExceptionErrorDialog
from calibre_plugins.epub_contributors_metadata.epub_editor import read_contributors, write_contributors

class VALUE:
    EMBED = 'embed'
    IMPORT = 'import'

PREFS = {}

class ePubContributorsMetadataAction(InterfaceAction):
    
    name = 'Edit Contributors Metadata'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Edit Contributors Metadata'), None, _('Edit the Contributors Metadata the ePub file'), None)
    #popup_type = QToolButton.MenuButtonPopup
    popup_type = QToolButton.InstantPopup
    action_type = 'current'
    dont_add_to = frozenset(['context-menu-device'])
    
    def genesis(self):
        self.is_library_selected = True
        self.menu = QMenu(self.gui)
        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(ICON.ALL)
        set_plugin_icon_resources(self.name, icon_resources)
        
        global PREFS
        PREFS = PREFSclass(self.gui)
        
        self.build_menus()
        
        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(ICON.PLUGIN))
        #self.qaction.triggered.connect(self.toolbar_triggered)
    
    def build_menus(self):
        self.menu.clear()
        
        create_menu_action_unique(self, self.menu, _('&Embed contributors'), None,
                                             triggered=self.embedContributors,
                                             unique_name='&Embed contributors')
        self.menu.addSeparator()
        
        create_menu_action_unique(self, self.menu, _('&Import contributors'), None,
                                             triggered=self.importContributors,
                                             unique_name='&Import contributors')
        self.menu.addSeparator()
        
        ## TODO
        ##
        ##create_menu_action_unique(self, self.menu, _('&Bulk avanced editor'), None,
        ##                                     triggered=self.editBulkContributors,
        ##                                     unique_name='&Bulk avanced editor')
        ##
        ##create_menu_action_unique(self, self.menu, _('&Avanced editor, book by book'), None,
        ##                                     triggered=self.editBookContributors,
        ##                                     unique_name='&Avanced editor, book by book')
        ##
        ##self.menu.addSeparator()
        
        create_menu_action_unique(self, self.menu, _('&Customize plugin...'), 'config.png',
                                             triggered=self.show_configuration,
                                             unique_name='&Customize plugin')
        
        self.gui.keyboard.finalize()
        
    
    def toolbar_triggered(self):
        self.embedContributors()
    
    def embedContributors(self):
        self.runContributorsProgressDialog({id:VALUE.EMBED for id in self.getBookIds()}) 
        
    def importContributors(self):
        self.runContributorsProgressDialog({id:VALUE.IMPORT for id in self.getBookIds()}) 
    
    def editBulkContributors(self):
        debug_print('editBulkContributors')
        PREFS()
        self.getBookIds()
        
    
    def editBookContributors(self):
        debug_print('editBookContributors')
        PREFS()
        self.getBookIds()
        
    
    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)
    
    def getBookIds(self):
        if not self.is_library_selected:
            error_dialog(self.gui, _('Could not to launch ePub Contributors Metadata'), _('No book selected'), show=True, show_copy_button=False)
            return []
        
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            error_dialog(self.gui, _('Could not to launch ePub Contributors Metadata'), _('No book selected'), show=True, show_copy_button=False)
            return []
        
        return self.gui.library_view.get_selected_ids()
    
    def runContributorsProgressDialog(self, book_ids):
        srpg = ePubContributorsProgressDialog(self, book_ids)
        srpg.close()
        del srpg


def set_new_size_DB(epub_path, book_id, dbAPI):
    
    new_size = os.path.getsize(epub_path)
    
    if new_size is not None:
        fname = dbAPI.fields['formats'].format_fname(book_id, 'EPUB')
        max_size = dbAPI.fields['formats'].table.update_fmt(book_id, 'EPUB', fname, new_size, dbAPI.backend)
        dbAPI.fields['size'].table.update_sizes({book_id:max_size})

class ePubContributorsProgressDialog(QProgressDialog):
    def __init__(self, plugin_action, book_ids):
        
        # plugin_action
        self.plugin_action = plugin_action
        # gui
        self.gui = self.plugin_action.gui
        
        # DB
        self.db = self.gui.current_db
        # DB API
        self.dbAPI = self.db.new_api
        
        # liste of book id
        self.book_ids = book_ids
        # Count book
        self.book_count = len(self.book_ids)
        
        # Count update
        self.no_epub_count = 0
        self.import_count = 0
        self.import_field_count = 0
        self.export_count = 0
        
        # Exception
        self.exception = None
        self.exception_unhandled = False
        
        self.time_execut = 0
        
        
        QProgressDialog.__init__(self, '', _('Cancel'), 0, self.book_count, self.gui)
        
        self.setWindowTitle(_('ePub Contributors Metadata Progress'))
        self.setWindowIcon(get_icon(ICON.PLUGIN))
        
        self.setValue(0)
        self.setMinimumWidth(500)
        self.setMinimumDuration(10)
        
        self.setAutoClose(True)
        self.setAutoReset(False)
        
        self.hide()
        debug_print('Launch ePub Contributors for {:d} books.\n'.format(self.book_count))
        
        QTimer.singleShot(0, self._run_search_replaces)
        self.exec_()
        
        #info debug
        debug_print('ePub Contributors launched for {:d} books.'.format(self.book_count))
        
        if self.wasCanceled():
            debug_print('ePub Contributors Metadata was aborted.')
        elif self.exception_unhandled:
            debug_print('ePub Contributors Metadata was interupted. An exception has occurred:\n'+str(self.exception))
            CustomExceptionErrorDialog(self.gui, self.exception, custome_msg=_('ePub Contributors Metadata encountered an unhandled exception.')+'\n')
        
        if self.no_epub_count:
            debug_print('{:d} books didn\'t have an ePub format.'.format(self.no_epub_count))
        
        if self.import_count:
            debug_print('Contributors read for {:d} books with a total of {:d} fields modify.'.format(self.import_count, self.import_field_count))
        else:
            debug_print('No Contributors read from books.')
        
        if self.export_count:
            debug_print('Contributors write for {:d} books.'.format(self.export_count))
        else:
            debug_print('No Contributors write in books.')
        
            debug_print('ePub Contributors execute in {:0.3f} seconds.\n'.format(self.time_execut))
            
        
        self.close()
    
    def close(self):
        QProgressDialog.close(self)
    
    
    def _run_search_replaces(self):
        start = time.time()
        alreadyOperationError = False
        typeString = type('')
        
        prefs = KEY_EXCLUDE_INVALIDE(PREFS(), self.gui)
        
        import_id = {}
        export_id = []
        no_epub_id = []
        
        self.setValue(0)
        self.show()
        
        for num, (book_id, contributors) in enumerate(self.book_ids.items(), 1):
            #update Progress
            self.setValue(num)
            self.setLabelText(_('Book {:d} of {:d}.').format(num, self.book_count))
            
            if self.book_count < 100:
                self.hide()
            else:
                self.show()
            
            ###
            epub_path = self.dbAPI.format_abspath(book_id, 'EPUB')
            miA = self.dbAPI.get_proxy_metadata(book_id)
            book_info = '"'+miA.get('title')+'" ('+' & '.join(miA.get('authors'))+') [book: '+str(num)+'/'+str(self.book_count)+']{id: '+str(book_id)+'}'
            
            if not epub_path:
                no_epub_id.append(book_id)
                debug_print('No ePub for', book_info,'\n')
                
            
            if epub_path:
                if contributors == VALUE.IMPORT:
                    contributors = read_contributors(epub_path)
                    
                    debug_print('Read ePub Contributors for', book_info,'\n')
                    
                    for k, v in prefs.items():
                        if k in contributors and miA.get(v) != contributors[k]:
                            self.dbAPI.set_field(v, {book_id:contributors[k]})
                            if book_id not in import_id:
                                import_id[book_id] = []
                            import_id[book_id].append(v)
                    
                else:
                    if contributors == VALUE.EMBED:
                        contributors = copy.deepcopy(prefs)
                    
                    debug_print('Write ePub Contributors for', book_info,'\n')
                    
                    for k, v in contributors.items():
                        if typeString == type(v):
                            contributors[k] = miA.get(v)
                    
                    for k, v in contributors.items():
                        if not v:
                            contributors[k] = []
                    
                    if write_contributors(epub_path, contributors):
                        set_new_size_DB(epub_path, book_id, self.dbAPI)
                        export_id.append(book_id)
                    
            
            #
        
        try:
            self.exception_unhandled = False
            
        except Exception as e:
            self.exception_unhandled = True
            self.exception = e
        
        self.no_epub_count = len(no_epub_id)
        self.export_count = len(export_id)
        self.import_count = len(import_id)
        self.import_field_count = 0
        for v in import_id.values():
            self.import_field_count += len(v)
        
        lst_id = list(import_id.keys()) + export_id
        self.gui.iactions['Edit Metadata'].refresh_gui(lst_id, covers_changed=False)
        
        self.time_execut = round(time.time() - start, 3)
        self.db.clean()
        self.hide()
