#!/usr/bin/env python

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'


try:
    load_translations()
except NameError:
    pass  # load_translations() added in calibre 1.9

import os.path
from typing import Any, Dict, List

try:
    from qt.core import QMenu, QToolButton
except ImportError:
    from PyQt5.Qt import QMenu, QToolButton

from calibre.gui2 import warning_dialog
from calibre.gui2.actions import InterfaceAction

from .common_utils import GUI, PLUGIN_NAME, debug_print, get_icon, has_restart_pending
from .common_utils.dialogs import ProgressDialog, custom_exception_dialog
from .common_utils.librarys import get_BookIds_selected
from .common_utils.menus import create_menu_action_unique
from .config import DYNAMIC, FIELD, ICON, KEY, plugin_check_enable_library, plugin_realy_enable
from .container_extended_metadata import default_extended_metadata, read_extended_metadata, write_extended_metadata


class VALUE:
    EMBED = 'embed'
    IMPORT = 'import'


class ePubExtendedMetadataAction(InterfaceAction):
    
    name = PLUGIN_NAME
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (PLUGIN_NAME, None, _('Edit the Extended Metadata of the ePub files'), None)
    popup_type = QToolButton.InstantPopup
    action_type = 'current'
    dont_add_to = frozenset(['context-menu-device'])
    
    def genesis(self):
        self.menu = QMenu(GUI)
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(ICON.PLUGIN))
        # self.qaction.triggered.connect(self.toolbar_triggered)
        self.rebuild_menus()
    
    def rebuild_menus(self):
        self.menu.clear()
        
        create_menu_action_unique(self, self.menu, _('&Embed Extended Metadata'), None,
                                        triggered=self.embed_extended_metadata,
                                        unique_name='&Embed Extended Metadata')
        self.menu.addSeparator()
        
        create_menu_action_unique(self, self.menu, _('&Import Extended Metadata'), None,
                                        triggered=self.import_extended_metadata,
                                        unique_name='&Import Extended Metadata')
        self.menu.addSeparator()
        
        ## TODO
        ##
        ## create_menu_action_unique(self, self.menu, _('&Bulk avanced editor'), None,
        ##                                     triggered=self.edit_bulk_extended_metadata,
        ##                                     unique_name='&Bulk avanced editor')
        ##
        ## create_menu_action_unique(self, self.menu, _('&Avanced editor, book by book'), None,
        ##                                     triggered=self.edit_book_extended_metadata,
        ##                                     unique_name='&Avanced editor, book by book')
        ##
        ## self.menu.addSeparator()
        
        create_menu_action_unique(self, self.menu, _('&Customize plugin…'), 'config.png',
                                        triggered=self.show_configuration,
                                        unique_name='&Customize plugin',
                                        shortcut=False)
        
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
        self.embed_extended_metadata()
    
    def embed_extended_metadata(self):
        self.run_extended_metadata({id:VALUE.EMBED for id in get_BookIds_selected(show_error=True)})
        
    def import_extended_metadata(self):
        self.run_extended_metadata({id:VALUE.IMPORT for id in get_BookIds_selected(show_error=True)})
    
    def edit_bulk_extended_metadata(self):
        debug_print('edit_bulk_extended_metadata')
    
    def edit_book_extended_metadata(self):
        debug_print('edit_book_extended_metadata')
    
    def run_extended_metadata(self, book_ids):
        ePubExtendedMetadataProgressDialog(book_ids)


def apply_extended_metadata(miA, prefs, extended_metadata, keep_calibre=False, check_user_metadata={}) -> List[str]:
    field_change = []
    
    if check_user_metadata:
        # check if the Metadata object accepts those added
        from calibre.ebooks.metadata import string_to_authors
        
        from .common_utils.columns import get_columns_from_dict
        miA_columns = get_columns_from_dict(miA.get_all_user_metadata(True))
        for k,cc in check_user_metadata.items():
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
                        value = join.joint(mc.metadata['#value#'])
                        
                        cc.metadata['#value#'] = value
                        cc.metadata['#extra#'] = None
                        miA.set_user_metadata(k, cc.metadata)
    
    contributors = extended_metadata[KEY.CONTRIBUTORS]
    for role, field in prefs.get(KEY.CONTRIBUTORS, {}).items():
        if field == FIELD.AUTHOR.NAME or role not in contributors:
            continue
        new_value = contributors[role]
        old_value = miA.get(field)
        if not (old_value and keep_calibre):
            miA.set(field, new_value)
            field_change.append(field)
    
    return field_change


def create_extended_metadata(miA, prefs) -> Dict[str, Any]:
    extended_metadata = default_extended_metadata()
    contributors = extended_metadata[KEY.CONTRIBUTORS]
    
    for role, field in prefs.get(KEY.CONTRIBUTORS, {}).items():
        contributors[role] = miA.get(field, default=[])
    
    return extended_metadata


class ePubExtendedMetadataProgressDialog(ProgressDialog):
    
    def setup_progress(self, **kvargs):
        # prefs
        self.prefs = KEY.get_current_prefs()
        
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
    
    def end_progress(self):
        
        # info debug
        debug_print(f'ePub Extended Metadata launched for {self.book_count} books.')
        
        if self.wasCanceled():
            debug_print('ePub Extended Metadata Metadata was aborted.')
        elif self.exception_unhandled:
            debug_print('ePub Extended Metadata Metadata was interupted. An exception has occurred:')
            debug_print(self.exception)
            custom_exception_dialog(self.exception)
        
        if self.exception_read:
            lst = []
            for id, book_info, e in self.exception_read:
                lst.append(f'Book {book_info} |> '+ e.__class__.__name__ +': '+ str(e))
            det_msg= '\n'.join(lst)
            
            warning_dialog(GUI, _('Exceptions during the reading of Extended Metadata'),
                _('{:d} exceptions have occurred during the reading of Extended Metadata.\n'
                'Some books may not have been updated.').format(len(self.exception_read)),
                det_msg='-- ePub Extended Metadata: reading exceptions --\n\n'+det_msg,
                show=True, show_copy_button=True,
            )
        
        if self.exception_write:
            lst = []
            for id, book_info, e in self.exception_write:
                lst.append(f'Book {book_info} |> '+ e.__class__.__name__ +': '+ str(e))
            det_msg= '\n'.join(lst)
            
            warning_dialog(GUI, _('Exceptions during the writing of Extended Metadata'),
                _('{:d} exceptions have occurred during the writing of Extended Metadata.\n'
                'Some books may not have been updated.').format(len(self.exception_write)),
                det_msg='-- ePub Extended Metadata: writing exceptions --\n\n'+det_msg,
                show=True, show_copy_button=True,
            )
        
        if self.no_epub_count:
            debug_print(f"{self.no_epub_count} books didn't have an ePub format.")
        
        if self.import_count:
            debug_print(
                f'Extended Metadata read for {self.import_count} books'
                f'with a total of {self.import_field_count} fields modify.'
            )
        else:
            debug_print('No Extended Metadata read from selected books.')
        
        if self.export_count:
            debug_print(f'Extended Metadata write for {self.export_count} books.')
        else:
            debug_print('No Extended Metadata write in selected books.')
            debug_print(f'ePub Extended Metadata execute in {self.time_execut:0.3f} seconds.', '\n')
    
    def job_progress(self):
        
        debug_print(f'Launch ePub Extended Metadata for {self.book_count} books.')
        debug_print(self.prefs)
        print()
        
        import_id = {}
        import_mi = {}
        
        export_id = []
        no_epub_id = []
        
        for book_id, action_type in self.book_ids.items():
            # update Progress
            num = self.increment()
            
            if self.wasCanceled():
                return
            
            ###
            miA = self.dbAPI.get_metadata(book_id, get_cover=False, get_user_categories=False)
            
            # book_info = "title" (author & author) [book: num/book_count]{id: book_id}
            book_info = '"{title}" ({authors}) [book: {num}/{book_count}]{{id: {book_id}}}'.format(
                title=miA.get('title'),
                authors=' & '.join(miA.get('authors')),
                num=num,
                book_count=self.book_count,
                book_id=book_id,
            )
            
            fmt = 'EPUB'
            path = self.dbAPI.format_abspath(book_id, fmt)
            
            if path:
                if action_type == VALUE.IMPORT:
                    if book_id not in import_mi:
                        debug_print('Read ePub Extended Metadata for', book_info, '\n')
                        extended_metadata = read_extended_metadata(path)
                        # try:
                        import_id[book_id] = apply_extended_metadata(
                            miA,
                            self.prefs,
                            extended_metadata,
                            keep_calibre=DYNAMIC[KEY.KEEP_CALIBRE_MANUAL],
                        )
                        if import_id[book_id]:
                            import_mi[book_id] = miA
                        # except Exception as err:
                        #     # title (author & author)
                        #     book_info = '"{title}" ({authors})'.format(
                        #         title=miA.get('title'), authors=' & '.join(miA.get('authors')),
                        #     )
                        #      self.exception_read.append( (id, book_info, err) )
                else:
                    debug_print('Write ePub Extended Metadata for', book_info, '\n')
                    if action_type == VALUE.EMBED:
                        extended_metadata = create_extended_metadata(miA, self.prefs)
                    
                    # try:
                    write_extended_metadata(path, extended_metadata)
                    export_id.append(book_id)
                    new_size = os.path.getsize(path)
                    if new_size is not None:
                        fname = self.dbAPI.fields['formats'].format_fname(book_id, fmt.upper())
                        max_size = self.dbAPI.fields['formats'].table.update_fmt(
                            book_id,
                            fmt.upper(),
                            fname,
                            new_size,
                            self.dbAPI.backend,
                        )
                        self.dbAPI.fields['size'].table.update_sizes({book_id:max_size})
                    
                    # except Exception as err:
                    #    # title (author & author)
                    #    book_info = '"{title}" ({authors})'.format(
                    #        title=miA.get('title'), authors=' & '.join(miA.get('authors')),
                    #    )
                    #     self.exception_write.append( (id, book_info, err) )
        
        for id, miA in import_mi.items():
            self.dbAPI.set_metadata(id, miA)
        
        self.no_epub_count = len(no_epub_id)
        self.export_count = len(export_id)
        self.import_count = len(import_id)
        self.import_field_count = 0
        for v in import_id.values():
            self.import_field_count += len(v)
        
        lst_id = list(import_id.keys()) + export_id
        GUI.iactions['Edit Metadata'].refresh_gui(lst_id, covers_changed=False)


####
# Enter the exotic zone
# those of the integrated plugins that if you don't watch out, overide those of Calibre => no basic metadata.

#   get_metadata(stream, type)
def read_metadata(stream, fmt, miA):
    # ---------------
    # Read Extended Metadata
    extended_metadata = read_extended_metadata(stream)
    apply_extended_metadata(miA, KEY.get_current_prefs(), extended_metadata,
                        keep_calibre=DYNAMIC[KEY.KEEP_CALIBRE_AUTO], check_user_metadata=KEY.get_current_columns())
    return miA


# ePubExtendedMetadata.MetadataWriter
#   set_metadata(stream, mi, type)
def write_metadata(stream, fmt, miA):
    import sys
    import traceback
    
    from calibre.customize.builtins import ActionEmbed
    
    # ---------------
    # Write Extended Metadata
    from calibre.customize.ui import find_plugin
    i, book_ids, pd, only_fmts, errors = find_plugin(ActionEmbed.name).actual_plugin_.job_data
    
    def report_error(mi, fmt, tb):
        miA.book_id = book_ids[i]
        errors.append((miA, fmt, tb))
    
    try:
        extended_metadata = create_extended_metadata(miA, KEY.get_current_prefs())
        write_extended_metadata(stream, extended_metadata)
    except:
        if report_error is None:
            debug_print(
                'Failed to set extended metadata for the', fmt.upper(),
                'format of:', getattr(miA, 'title', ''),
                file=sys.stderr,
            )
            traceback.print_exc()
        else:
            report_error(miA, fmt.upper(), traceback.format_exc())
