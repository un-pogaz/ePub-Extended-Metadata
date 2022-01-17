#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'
__docformat__ = 'restructuredtext en'

import os, time
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
from calibre.ebooks.metadata.book.base import Metadata
from calibre.constants import numeric_version as calibre_version
from calibre.gui2 import error_dialog, warning_dialog, question_dialog, info_dialog
from calibre.gui2.actions import InterfaceAction
from calibre.library import current_library_name
from polyglot.builtins import iteritems

from calibre_plugins.edit_contributors_metadata.config import ICON
from calibre_plugins.edit_contributors_metadata.common_utils import set_plugin_icon_resources, get_icon, create_menu_action_unique, create_menu_item, debug_print, CustomExceptionErrorDialog


class EditContributorsMetadataAction(InterfaceAction):
    
    name = 'Edit Contributors Metadata'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = ('Edit Contributors Metadata', None, _('Apply a list of multiple saved Find and Replace operations'), None)
    popup_type = QToolButton.InstantPopup
    action_type = 'current'
    dont_add_to = frozenset(['context-menu-device'])
    
    def genesis(self):
        self.is_library_selected = True
        self.menu = QMenu(self.gui)
        
        icon_resources = self.load_resources(ICON.ALL)
        set_plugin_icon_resources(self.name, icon_resources)
        
        
        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(ICON.PLUGIN))
    
    def initialization_complete(self):
        # we implement here to have access to current_db
        # if we try this in genesis() we get the error:
        # AttributeError: 'Main' object has no attribute 'current_db'
        
        create_menu_action_unique(self, self.menu, _('&Embed contributors'), None,
                                             triggered=self.embedContributors,
                                             unique_name='&Embed contributors')
        
        create_menu_action_unique(self, self.menu, _('&Import contributors'), None,
                                             triggered=self.importContributors,
                                             unique_name='&Import contributors')
        self.menu.addSeparator()
        
        create_menu_action_unique(self, self.menu, _('&Avanced editor'), None,
                                             triggered=self.editContributors,
                                             unique_name='&Avanced editor')
        
        self.menu.addSeparator()
        
        create_menu_action_unique(self, self.menu, _('&Customize plugin...'), 'config.png',
                                             triggered=self.show_configuration,
                                             unique_name='&Customize plugin')
        
        self.gui.keyboard.finalize
    
    def embedContributors(self):
        
        return None
        
    def importContributors(self):
        
        return None
    
    def editContributors(self):
        
        return None
    
    def writeContributors(self, contributors):
        
        if not self.is_library_selected:
            return error_dialog(self.gui, _('Could not to launch Edit Contributors Metadata'), _('No book selected'), show=True, show_copy_button=False)
        
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return error_dialog(self.gui, _('Could not to launch Edit Contributors Metadata'), _('No book selected'), show=True, show_copy_button=False)
        
        book_ids = self.gui.library_view.get_selected_ids()
        
        srpg = EditContributorsProgressDialog(self, book_ids, contributors)
        srpg.close()
        del srpg
    
    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)



class EditContributorsProgressDialog(QProgressDialog):
    def __init__(self, plugin_action, book_ids, contributors):
        
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
        self.books_update = 0
        self.fields_update = 0
        
        
        
        
        # Count of Search/Replace
        self.operation_count = len(self.operation_list)
        
        # Count of Search/Replace
        self.total_operation_count = self.book_count*self.operation_count
        
        
        # Exception
        self.exception = []
        self.exception_unhandled = False
        self.exception_update = False
        self.exception_safely = False
        
        self.time_execut = 0
        
        
        QProgressDialog.__init__(self, '', _('Cancel'), 0, self.total_operation_count, self.gui)
        
        self.setWindowTitle(_('Edit Contributors Metadata Progress'))
        self.setWindowIcon(get_icon(ICON.PLUGIN))
        
        self.setValue(0)
        self.setMinimumWidth(500)
        self.setMinimumDuration(10)
        
        self.setAutoClose(True)
        self.setAutoReset(False)
        
        self.hide()
        debug_print('Launch Edit Contributors for {:d} books.\n'.format(self.book_count))
        
        QTimer.singleShot(0, self._run_search_replaces)
        self.exec_()
        
        
        if self.wasCanceled():
            debug_print('Edit Contributors Metadata was cancelled. No change.')
        
        elif self.exception_unhandled:
            debug_print('Edit Contributors Metadata was interupted. An exception has occurred:\n'+str(self.exception))
            CustomExceptionErrorDialog(self.gui ,self.exception, custome_msg=_('Mass Search/Replace encountered an unhandled exception.')+'\n')
        
        else:
            
            #info debug
            debug_print('Edit Contributors launched for {:d} books.'.format(self.book_count, self.operation_count))
            
            debug_print('Search/Replace execute in {:0.3f} seconds.\n'.format(self.time_execut))
            
        
        self.close()
    
    def close(self):
        self.s_r.close()
        QProgressDialog.close(self)
    
    
    def _run_search_replaces(self):
        lst_id = []
        book_id_update = defaultdict(dict)
        start = time.time()
        alreadyOperationError = False
        try:
            self.setValue(0)
            self.show()
            
        
        except Exception as e:
            self.exception_unhandled = True
            self.exception = e
        
        else:
            
            lst_id = []
            for field, book_id_val_map in iteritems(self.s_r.updated_fields):
                lst_id += book_id_val_map.keys()
            self.fields_update = len(lst_id)
            
            lst_id = list(dict.fromkeys(lst_id))
            self.books_update = len(lst_id)
            
            book_id_update = defaultdict(dict)
            
            if self.books_update > 0:
                
                debug_print('Update the database for {:d} books with a total of {:d} fields...\n'.format(self.books_update, self.fields_update))
                self.setLabelText(_('Update the library for {:d} books with a total of {:d} fields...').format(self.books_update, self.fields_update))
                self.setValue(self.total_operation_count)
                
                if self.exceptionStrategy == ERROR_UPDATE.SAFELY or self.exceptionStrategy == ERROR_UPDATE.DONT_STOP:
                    
                    dont_stop = self.exceptionStrategy == ERROR_UPDATE.DONT_STOP
                    
                    if self.exception:
                        self.exception_safely = True
                    
                    for id in iter(lst_id):
                        if self.exception and not dont_stop:
                            break
                        for field, book_id_val_map in iteritems(self.s_r.updated_fields):
                            if self.exception and not dont_stop:
                                break
                            if id in book_id_val_map:
                                try:
                                    val = self.s_r.updated_fields[field][id]
                                    self.dbAPI.set_field(field, {id:val})
                                    book_id_update[field][id] = ''
                                except Exception as e:
                                    self.exception_safely = True
                                    
                                    miA = self.dbAPI.get_proxy_metadata(id)
                                    #title (author & author)
                                    book_info = '"'+miA.get('title')+'" ('+' & '.join(miA.get('authors'))+')'
                                    self.exception.append( (id, book_info, field, e) )
                    
                else:
                    try:
                        
                        backup_fields = None
                        is_restore = self.exceptionStrategy == ERROR_UPDATE.RESTORE
                        if is_restore:
                            backup_fields = defaultdict(dict)
                        
                        if self.exception:
                            raise Exception('raise')
                        
                        for field, book_id_val_map in iteritems(self.s_r.updated_fields):
                            if is_restore:
                                src_field = self.dbAPI.all_field_for(field, book_id_val_map.keys())
                                backup_fields[field] = src_field
                            
                            self.dbAPI.set_field(field, book_id_val_map)
                            book_id_update[field] = {id:'' for id in book_id_val_map.keys()}
                        
                    except Exception as e:
                        self.exception_update = True
                        self.exception.append( (None, None, None, e) )
                        
                        if is_restore:
                            for field, book_id_val_map in iteritems(backup_fields):
                               self.dbAPI.set_field(field, book_id_val_map)
                
                self.gui.iactions['Edit Metadata'].refresh_gui(lst_id, covers_changed=False)
                
            
        
        finally:
            
            lst_id = []
            for field, book_id_map in iteritems(book_id_update):
                lst_id += book_id_map.keys()
            self.fields_update = len(lst_id)
            
            lst_id = list(dict.fromkeys(lst_id))
            self.books_update = len(lst_id)
            
            self.time_execut = round(time.time() - start, 3)
            self.db.clean()
            self.hide()
