#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'
__docformat__ = 'restructuredtext en'



try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

# The class that all Interface Action plugin wrappers must inherit from
from calibre.customize import InterfaceActionBase, FileTypePlugin

DEBUG_PRE = 'ePubContributorsMetadata'

class ActionMassSearchReplace(InterfaceActionBase):  ## FileTypePlugin
    '''
    This class is a simple wrapper that provides information about the actual
    plugin class. The actual interface plugin class is called InterfacePlugin
    and is defined in the ui.py file, as specified in the actual_plugin field
    below.
    
    The reason for having two classes is that it allows the command line
    calibre utilities to run without needing to load the GUI libraries.
    '''
    name                    = 'Edit Contributors Metadata'
    description             = _('Read and Write the Contributors Metadata in the ePub file')
    supported_platforms     = ['windows', 'osx', 'linux']
    author                  = 'un_pogaz'
    version                 = (0, 1, 0)
    minimum_calibre_version = (4, 0, 0)
    
    #: This field defines the GUI plugin class that contains all the code
    #: that actually does something. Its format is module_path:class_name
    #: The specified class must be defined in the specified module.
    actual_plugin           = 'calibre_plugins.edit_contributors_metadata.action:EditContributorsMetadataAction'
    
    def is_customizable(self):
        '''
        This method must return True to enable customization via
        Preferences->Plugins
        '''
        return True
    
    
    def config_widget(self):
        '''
        Implement this method and :meth:`save_settings` in your plugin to
        use a custom configuration dialog.

        This method, if implemented, must return a QWidget. The widget can have
        an optional method validate() that takes no arguments and is called
        immediately after the user clicks OK. Changes are applied if and only
        if the method returns True.

        If for some reason you cannot perform the configuration at this time,
        return a tuple of two strings (message, details), these will be
        displayed as a warning dialog to the user and the process will be
        aborted.

        The base class implementation of this method raises NotImplementedError
        so by default no user configuration is possible.
        '''
        # It is important to put this import statement here rather than at the
        # top of the module as importing the config class will also cause the
        # GUI libraries to be loaded, which we do not want when using calibre
        # from the command line
        if self.actual_plugin_:
            from calibre_plugins.edit_contributors_metadata.config import ConfigWidget
            return ConfigWidget(self.actual_plugin_)
    
    def save_settings(self, config_widget):
        '''
        Save the settings specified by the user with config_widget.

        :param config_widget: The widget returned by :meth:`config_widget`.
        '''
        config_widget.save_settings()
    
    
##########
#class FileTypePlugin(Plugin):
    '''
    A plugin that is associated with a particular set of file types.
    '''
    
    #: Set of file types for which this plugin should be run.
    #: Use '*' for all file types.
    #: For example: ``{'lit', 'mobi', 'prc'}``
    file_types     = set('EPUB')
    
    #: If True, this plugin is run when books are added
    #: to the database
    on_import      = True
    
    #: If True, this plugin is run after books are added
    #: to the database. In this case the postimport and postadd
    #: methods of the plugin are called.
    on_postimport  = True
    
    #: If True, this plugin is run just before a conversion
    on_preprocess  = False
    
    #: If True, this plugin is run after conversion
    #: on the final file produced by the conversion output plugin.
    on_postprocess = False
    
    #type = _('File type')
    
    def run(self, path_to_ebook):
        '''
        Run the plugin. Must be implemented in subclasses.
        It should perform whatever modifications are required
        on the e-book and return the absolute path to the
        modified e-book. If no modifications are needed, it should
        return the path to the original e-book. If an error is encountered
        it should raise an Exception. The default implementation
        simply return the path to the original e-book. Note that the path to
        the original file (before any file type plugins are run, is available as
        self.original_path_to_file).
        
        The modified e-book file should be created with the
        :meth:`temporary_file` method.
        
        :param path_to_ebook: Absolute path to the e-book.
        
        :return: Absolute path to the modified e-book.
        '''
        # Default implementation does nothing
        print('|| FileTypePlugin | path_to_ebook' + str(path_to_ebook))
        return path_to_ebook
    
    def postimport(self, book_id, book_format, db):
        '''
        Called post import, i.e., after the book file has been added to the database. Note that
        this is different from :meth:`postadd` which is called when the book record is created for
        the first time. This method is called whenever a new file is added to a book record. It is
        useful for modifying the book record based on the contents of the newly added file.
    
        :param book_id: Database id of the added book.
        :param book_format: The file type of the book that was added.
        :param db: Library database.
        '''
        print('|| FileTypePlugin | path_to_ebook')
        pass  # Default implementation does nothing
    
    def postadd(self, book_id, fmt_map, db):
        '''
        Called post add, i.e. after a book has been added to the db. Note that
        this is different from :meth:`postimport`, which is called after a single book file
        has been added to a book. postadd() is called only when an entire book record
        with possibly more than one book file has been created for the first time.
        This is useful if you wish to modify the book record in the database when the
        book is first added to calibre.
        
        :param book_id: Database id of the added book.
        :param fmt_map: Map of file format to path from which the file format
            was added. Note that this might or might not point to an actual
            existing file, as sometimes files are added as streams. In which case
            it might be a dummy value or a non-existent path.
        :param db: Library database
        '''
        print('|| FileTypePlugin | postadd')
        pass  # Default implementation does nothing
    


# }}}
# For testing, run from command line with this:
# calibre-debug -e __init__.py
if __name__ == '__main__':
    try:
        from qt.core import QApplication
    except ImportError:
        from PyQt5.Qt import QApplication
    from calibre.gui2.preferences import test_widget
    app = QApplication([])
    test_widget('Advanced', 'Plugins')
