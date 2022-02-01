#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'
__docformat__ = 'restructuredtext en'

import copy, time, os
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
    from qt.core import QToolButton, QMenu, QProgressDialog, QTimer, QSize
except ImportError:
    from PyQt5.Qt import QToolButton, QMenu, QProgressDialog, QTimer, QSize

from calibre import prints
from calibre.constants import numeric_version as calibre_version
from calibre.gui2 import error_dialog, warning_dialog, question_dialog, info_dialog
from calibre.gui2.actions import InterfaceAction
from calibre.gui2.ui import get_gui

from .config import ICON, DYNAMIC, FIELD, KEY, plugin_check_enable_library, plugin_realy_enable
from .common_utils import (debug_print, get_icon, PLUGIN_NAME, current_db, get_selected_BookIds, load_plugin_resources,
                            create_menu_action_unique, has_restart_pending, CustomExceptionErrorDialog)
from .container_extended_metadata import read_extended_metadata, write_extended_metadata

GUI = get_gui()

class VALUE:
    EMBED = 'embed'
    IMPORT = 'import'


class ePubExtendedMetadataAction(InterfaceAction):
    
    name = PLUGIN_NAME
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (PLUGIN_NAME, None, _('Edit the Extended Metadata of the ePub files'), None)
    #popup_type = QToolButton.MenuButtonPopup
    popup_type = QToolButton.InstantPopup
    action_type = 'current'
    dont_add_to = frozenset(['context-menu-device'])
    
    def genesis(self):
        self.is_library_selected = True
        self.menu = QMenu(GUI)
        # Read the plugin icons and store for potential sharing with the config widget
        load_plugin_resources(self.plugin_path, ICON.ALL)
        
        self.rebuild_menus()
        
        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(ICON.PLUGIN))
        #self.qaction.triggered.connect(self.toolbar_triggered)
    
    def rebuild_menus(self):
        self.menu.clear()
        
        create_menu_action_unique(self, self.menu, _('&Embed Extended Metadata'), None,
                                             triggered=self.embedExtendedMetadata,
                                             unique_name='&Embed Extended Metadata')
        self.menu.addSeparator()
        
        create_menu_action_unique(self, self.menu, _('&Import Extended Metadata'), None,
                                             triggered=self.importExtendedMetadata,
                                             unique_name='&Import Extended Metadata')
        self.menu.addSeparator()
        
        ## TODO
        ##
        ##create_menu_action_unique(self, self.menu, _('&Bulk avanced editor'), None,
        ##                                     triggered=self.editBulkExtendedMetadata,
        ##                                     unique_name='&Bulk avanced editor')
        ##
        ##create_menu_action_unique(self, self.menu, _('&Avanced editor, book by book'), None,
        ##                                     triggered=self.editBookExtendedMetadata,
        ##                                     unique_name='&Avanced editor, book by book')
        ##
        ##self.menu.addSeparator()
        
        create_menu_action_unique(self, self.menu, _('&Customize plugin...'), 'config.png',
                                             triggered=self.show_configuration,
                                             unique_name='&Customize plugin')
        
        GUI.keyboard.finalize()
    
    def show_configuration(self):
        if not has_restart_pending():
            self.interface_action_base_plugin.do_user_config(GUI)
    
    def library_changed(self, db):
        plugin_check_enable_library()
    
    def gui_layout_complete(self):
        '''
        Called once per action when the layout of the main GUI is
        completed. If your action needs to make changes to the layout, they
        should be done here, rather than in :meth:`initialization_complete`.
        '''
        plugin_check_enable_library()
    
    def shutting_down(self):
        '''
        Called once per plugin when the main GUI is in the process of shutting
        down. Release any used resources, but try not to block the shutdown for
        long periods of time.
        
        :return: False to halt the shutdown. You are responsible for telling
                 the user why the shutdown was halted.
        
        '''
        plugin_realy_enable(KEY.AUTO_IMPORT)
        plugin_realy_enable(KEY.AUTO_EMBED)
        return True
    
    
    def toolbar_triggered(self):
        self.embedExtendedMetadata()
    
    def embedExtendedMetadata(self):
        self.runExtendedMetadataProgressDialog({id:VALUE.EMBED for id in get_selected_BookIds()}) 
        
    def importExtendedMetadata(self):
        self.runExtendedMetadataProgressDialog({id:VALUE.IMPORT for id in get_selected_BookIds()}) 
    
    def editBulkExtendedMetadata(self):
        debug_print('editBulkExtendedMetadata')
        
    
    def editBookExtendedMetadata(self):
        debug_print('editBookExtendedMetadata')
        
    
    
    def runExtendedMetadataProgressDialog(self, book_ids):
        srpg = ePubExtendedMetadataProgressDialog(book_ids)
        srpg.close()
        del srpg

def apply_extended_metadata(miA, prefs, extended_metadata, keep_calibre=False, check_user_metadata={}):
    field_change = []
    
    print('len(check_user_metadata):'+str(len(check_user_metadata)))
    
    if check_user_metadata:
        #check if the Metadata object accepts those added
        from .columns_metadata import get_columns_from_dict, string_to_authors
        miA_columns = get_columns_from_dict(miA.get_all_user_metadata(True))
        miA_init_len = len(miA_columns)
        for k,cc in iteritems(check_user_metadata):
            if not (cc.is_composite or cc.is_csp):
                if k not in miA_columns:
                    if cc.is_multiple:
                        cc.metadata['#value#'] = []
                    else:
                        cc.metadata['#value#'] = None
                    cc.metadata['#extra#'] = None
                    miA.set_user_metadata(k, cc.metadata)
                else:
                    mc = miA_columns[k]
                    if cc.is_multiple and not mc.is_multiple:
                        values = []
                        if cc.is_names:
                            values = string_to_authors(mc.metadata['#value#'])
                        elif mc.metadata['#value#']:
                            values = mc.metadata['#value#'].split(cc.is_multiple.ui_to_list)
                        
                        cc.metadata['#value#'] = values
                        cc.metadata['#extra#'] = None
                        miA.set_user_metadata(k, cc.metadata)
                    
                    if not cc.is_multiple and mc.is_multiple:
                        join = mc.is_multiple.list_to_ui or ', '
                        values = join.joint(mc.metadata['#value#'])
                        
                        cc.metadata['#value#'] = value
                        cc.metadata['#extra#'] = None
                        miA.set_user_metadata(k, cc.metadata)
    
    
    for data, field in iteritems(prefs):
        if data == KEY.CONTRIBUTORS:
            for role, field in iteritems(prefs[KEY.CONTRIBUTORS]):
                if field != FIELD.AUTHOR.NAME and role in extended_metadata[KEY.CONTRIBUTORS]:
                    new_value = extended_metadata[KEY.CONTRIBUTORS][role]
                    old_value = miA.get(field)
                    if not (old_value and keep_calibre):
                        miA.set(field, new_value)
                        field_change.append(field)
        else:
            new_value = extended_metadata[data]
            if new_value != miA.get(field):
                miA.set(field, new_value)
                field_change.append(field)
    
    return field_change

def create_extended_metadata(miA, prefs):
    extended_metadata = {}
    for data, field in iteritems(prefs):
        if data == KEY.CONTRIBUTORS:
            extended_metadata[KEY.CONTRIBUTORS] = {}
            for role, field in iteritems(prefs[KEY.CONTRIBUTORS]):
                extended_metadata[KEY.CONTRIBUTORS][role] = miA.get(field, default=[])
        else:
            extended_metadata[data] = miA.get(field, default=None)
    
    return extended_metadata


class ePubExtendedMetadataProgressDialog(QProgressDialog):
    def __init__(self, book_ids):
        # DB
        self.db = current_db()
        # DB API
        self.dbAPI = self.db.new_api
        
        # prefs
        self.prefs = KEY.get_current_prefs()
        
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
        self.exception_read = []
        self.exception_write = []
        
        self.time_execut = 0
        
        
        QProgressDialog.__init__(self, '', _('Cancel'), 0, self.book_count, GUI)
        
        self.setWindowTitle(_('ePub Extended Metadata progress').format(PLUGIN_NAME))
        self.setWindowIcon(get_icon(ICON.PLUGIN))
        
        self.setValue(0)
        self.setMinimumWidth(500)
        self.setMinimumDuration(10)
        
        self.setAutoClose(True)
        self.setAutoReset(False)
        
        self.hide()
        debug_print('Launch ePub Extended Metadata for {:d} books.'.format(self.book_count))
        debug_print(self.prefs,'\n')
        
        QTimer.singleShot(0, self._run_contributors)
        self.exec_()
        
        #info debug
        debug_print('ePub Extended Metadata launched for {:d} books.'.format(self.book_count))
        
        if self.wasCanceled():
            debug_print('ePub Extended Metadata Metadata was aborted.')
        elif self.exception_unhandled:
            debug_print('ePub Extended Metadata Metadata was interupted. An exception has occurred:\n'+str(self.exception))
            CustomExceptionErrorDialog(self.exception)
        
        if self.exception_read:
            
            det_msg= '\n'.join('Book {:s} |> {:}'.format(book_info, e.__class__.__name__ +': '+ str(e)) for id, book_info, e in self.exception_read)
            
            warning_dialog(GUI, _('Exceptions during the reading of Extended Metadata'),
                        _('{:d} exceptions have occurred during the reading of Extended Metadata.\nSome books may not have been updated.').format(len(self.exception_read)),
                            det_msg='-- ePub Extended Metadata: reading exceptions --\n\n'+det_msg, show=True, show_copy_button=True)
        
        if self.exception_write:
            
            det_msg= '\n'.join('Book {:s} |> {:}'.format(book_info, e.__class__.__name__ +': '+ str(e)) for id, book_info, e in self.exception_write)
            
            warning_dialog(GUI, _('Exceptions during the writing of Extended Metadata'),
                        _('{:d} exceptions have occurred during the writing of Extended Metadata.\nSome books may not have been updated.').format(len(self.exception_write)),
                            det_msg='-- ePub Extended Metadata: writing exceptions --\n\n'+det_msg, show=True, show_copy_button=True)
        
        
        if self.no_epub_count:
            debug_print('{:d} books didn\'t have an ePub format.'.format(self.no_epub_count))
        
        if self.import_count:
            debug_print('Extended Metadata read for {:d} books with a total of {:d} fields modify.'.format(self.import_count, self.import_field_count))
        else:
            debug_print('No Extended Metadata read from selected books.')
        
        if self.export_count:
            debug_print('Extended Metadata write for {:d} books.'.format(self.export_count))
        else:
            debug_print('No Extended Metadata write in selected books.')
        
            debug_print('ePub Extended Metadata execute in {:0.3f} seconds.\n'.format(self.time_execut))
            
        
        self.close()
    
    def close(self):
        QProgressDialog.close(self)
    
    
    def _run_contributors(self):
        start = time.time()
        alreadyOperationError = False
        typeString = type('')
        
        import_id = {}
        import_mi = {}
        
        export_id = []
        no_epub_id = []
        
        self.setValue(0)
        self.show()
        
        
        for num, (book_id, extended_metadata) in enumerate(iteritems(self.book_ids), 1):
            #update Progress
            self.setValue(num)
            self.setLabelText(_('Book {:d} of {:d}.').format(num, self.book_count))
            
            if self.book_count < 100:
                self.hide()
            else:
                self.show()
            
            if self.wasCanceled():
                self.close()
                return
            
            ###
            miA = self.dbAPI.get_metadata(book_id, get_cover=False, get_user_categories=False)
            book_info = '"'+miA.get('title')+'" ('+' & '.join(miA.get('authors'))+') [book: '+str(num)+'/'+str(self.book_count)+']{id: '+str(book_id)+'}'
            
            fmt = 'EPUB'
            path = self.dbAPI.format_abspath(book_id, fmt)
            
            if path:
                if extended_metadata == VALUE.IMPORT:
                    if book_id not in import_mi:
                        debug_print('Read ePub Extended Metadata for', book_info,'\n')
                        extended_metadata = read_extended_metadata(path)
                        #try:
                        import_id[book_id] = apply_extended_metadata(miA, self.prefs, extended_metadata, keep_calibre=DYNAMIC[KEY.KEEP_CALIBRE_MANUAL])
                        if import_id[book_id]:
                            import_mi[book_id] = miA
                        #except Exception as err:
                        #    #title (author & author)
                        #    book_info = '"'+miA.get('title')+'" ('+' & '.join(miA.get('authors'))+')'
                        #    self.exception_read.append( (id, book_info, err) )
                else:
                    debug_print('Write ePub Extended Metadata for', book_info+'\n')
                    if extended_metadata == VALUE.EMBED:
                        extended_metadata = create_extended_metadata(miA, self.prefs)
                    
                    #try:
                    write_extended_metadata(path, extended_metadata)
                    export_id.append(book_id)
                    new_size = os.path.getsize(path)
                    if new_size is not None:
                        fname = self.dbAPI.fields['formats'].format_fname(book_id, fmt.upper())
                        max_size = self.dbAPI.fields['formats'].table.update_fmt(book_id, fmt.upper(), fname, new_size, self.dbAPI.backend)
                        self.dbAPI.fields['size'].table.update_sizes({book_id:max_size})
                    
                    #except Exception as err:
                    #    #title (author & author)
                    #    book_info = '"'+miA.get('title')+'" ('+' & '.join(miA.get('authors'))+')'
                    #    self.exception_write.append( (id, book_info, err) )
        
        
        
        
        for id, miA in iteritems(import_mi):
            self.dbAPI.set_metadata(book_id, miA)
        
        self.no_epub_count = len(no_epub_id)
        self.export_count = len(export_id)
        self.import_count = len(import_id)
        self.import_field_count = 0
        for v in itervalues(import_id):
            self.import_field_count += len(v)
        
        lst_id = list(import_id.keys()) + export_id
        GUI.iactions['Edit Metadata'].refresh_gui(lst_id, covers_changed=False)
        
        self.time_execut = round(time.time() - start, 3)
        self.db.clean()
        self.hide()


####
# Enter the exotic zone
# those of the integrated plugins that if you don't watch out, overide those of Calibre => no basic metadata.

import sys, traceback
from calibre.customize.ui import find_plugin, quick_metadata, apply_null_metadata, force_identifiers, config, _metadata_readers
from calibre.customize.builtins import EPUBMetadataReader, EPUBMetadataWriter, OPFMetadataReader, ActionEmbed
from calibre.ebooks.metadata.opf import set_metadata as set_metadata_opf

# ePubExtendedMetadata.MetadataReader
#   get_metadata(stream, type)
def read_metadata(stream, fmt):
    # Use the Calibre EPUBMetadataReader
    fmt = fmt.lower().strip()
    print('fmt='+fmt)
    try:
        if hasattr(stream, 'seek'): stream.seek(0)
        calibre_reader = find_plugin(EPUBMetadataReader.name)
        calibre_reader.quick = quick_metadata.quick
        miA = calibre_reader.get_metadata(stream, fmt)
    except:
        traceback.print_exc()
    else:
        #---------------
        # Read Extended Metadata
        if hasattr(stream, 'seek'): stream.seek(0)
        extended_metadata = read_extended_metadata(stream)
        apply_extended_metadata(miA, KEY.get_current_prefs(), extended_metadata,
                            keep_calibre=DYNAMIC[KEY.KEEP_CALIBRE_AUTO], check_user_metadata=KEY.get_current_columns())
        return miA

# ePubExtendedMetadata.MetadataWriter
#   set_metadata(stream, mi, type)
def write_metadata(stream, miA, fmt):
    # Use the Calibre EPUBMetadataWriter
    fmt = fmt.lower().strip()
    embed = find_plugin(ActionEmbed.name)
    i, book_ids, pd, only_fmts, errors = embed.actual_plugin_.job_data
    
    def report_error(mi, fmt, tb):
        miA.book_id = book_ids[i]
        errors.append((miA, fmt, tb))
    
    try:
        if hasattr(stream, 'seek'): stream.seek(0)
        calibre_writer = find_plugin(EPUBMetadataWriter.name)
        calibre_writer.apply_null = apply_null_metadata.apply_null
        calibre_writer.force_identifiers = force_identifiers.force_identifiers
        calibre_writer.site_customization = config['plugin_customization'].get(calibre_writer.name, '')
        calibre_writer.set_metadata(stream, miA, fmt)
        
    except:
        if report_error is None:
            from calibre import prints
            prints('Failed to set metadata for the \'{:s}\' format of: '.format(fmt.upper(), getattr(miA, 'title', '')), file=sys.stderr)
            traceback.print_exc()
        else:
            report_error(miA, fmt.upper(), traceback.format_exc())
    else:
        #---------------
        # Write Extended Metadata
        try:
            if hasattr(stream, 'seek'): stream.seek(0)
            extended_metadata = create_extended_metadata(miA, KEY.get_current_prefs())
            write_extended_metadata(stream, extended_metadata)
        except:
            if report_error is None:
                from calibre import prints
                prints('Failed to set extended metadata for the', fmt.upper(), 'format of:', getattr(miA, 'title', ''), file=sys.stderr)
                traceback.print_exc()
            else:
                report_error(miA, fmt.upper(), traceback.format_exc())
