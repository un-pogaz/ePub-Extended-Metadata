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
PREFS_NAMESPACE = 'ePubContributorsMetadata'

class ActionMassSearchReplace(InterfaceActionBase, FileTypePlugin):  ## FileTypePlugin
    '''
    This class is a simple wrapper that provides information about the actual
    plugin class. The actual interface plugin class is called InterfacePlugin
    and is defined in the ui.py file, as specified in the actual_plugin field
    below.
    
    The reason for having two classes is that it allows the command line
    calibre utilities to run without needing to load the GUI libraries.
    '''
    name                    = 'ePub Contributors Metadata'
    description             = _('Read and Write the Contributors Metadata in the ePub file')
    supported_platforms     = ['windows', 'osx', 'linux']
    author                  = 'un_pogaz'
    version                 = (0, 1, 0)
    minimum_calibre_version = (4, 0, 0)
    
    #: This field defines the GUI plugin class that contains all the code
    #: that actually does something. Its format is module_path:class_name
    #: The specified class must be defined in the specified module.
    actual_plugin           = 'calibre_plugins.epub_contributors_metadata.action:ePubContributorsMetadataAction'
    
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
            from calibre_plugins.epub_contributors_metadata.config import ConfigWidget
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
    file_types     = {'epub'}
    
    #: If True, this plugin is run when books are added
    #: to the database
    on_import      = False
    
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
    
    def postadd(self, book_id, fmt_map, db):
        global import_postadd 
        if not import_postadd:
            import importlib
            import_postadd = getattr(importlib.import_module('calibre_plugins.epub_contributors_metadata.action'), 'import_postadd', None )
        
        if import_postadd:
            import_postadd(book_id, fmt_map, db)


import_postadd = None

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
