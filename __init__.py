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
from calibre.customize import InterfaceActionBase, MetadataReaderPlugin, MetadataWriterPlugin


def import_attribute(module_name, attribute):
    import importlib
    return getattr(importlib.import_module('.'+module_name, __name__), attribute, None )


DEBUG_PRE = 'ePubExtendedMetadata'
PREFS_NAMESPACE = 'ePubExtendedMetadata'

FILES_TYPES             = {'epub'}
class NAME:
    BASE                = 'ePub Extended Metadata'
    READER              = BASE + ' {Reader}'
    WRITER              = BASE + ' {Writer}'
class DESCRIPTION:
    ACTION              = _('Read and write a wider range of metadata for ePub\'s files and associating them to columns in your libraries.')
    COMPANION            = '\n' +_('This is an companion and embeded plugin of "{:s}".').format(NAME.BASE)
    READER              = _('Write a wider range of metadata in the ePub file.') + COMPANION
    WRITER              = _('Read a wider range of metadata from the ePub file.') + COMPANION
SUPPORTED_PLATFORMS     = ['windows', 'osx', 'linux']
AUTHOR                  = 'un_pogaz'
VERSION                 = (-1,-1,-1)
MINIMUM_CALIBRE_VERSION = (4, 0, 0)


class ePubExtendedMetadata(InterfaceActionBase):
    '''
    This class is a simple wrapper that provides information about the actual
    plugin class. The actual interface plugin class is called InterfacePlugin
    and is defined in the ui.py file, as specified in the actual_plugin field
    below.
    
    The reason for having two classes is that it allows the command line
    calibre utilities to run without needing to load the GUI libraries.
    '''
    name                    = NAME.BASE
    description             = DESCRIPTION.ACTION
    supported_platforms     = SUPPORTED_PLATFORMS
    author                  = AUTHOR
    version                 = VERSION
    minimum_calibre_version = MINIMUM_CALIBRE_VERSION
    
    
    #: This field defines the GUI plugin class that contains all the code
    #: that actually does something. Its format is module_path:class_name
    #: The specified class must be defined in the specified module.
    actual_plugin           = __name__+'.action:ePubExtendedMetadataAction'
    
    
    def initialize(self):
        '''
        Called once when calibre plugins are initialized.  Plugins are
        re-initialized every time a new plugin is added. Also note that if the
        plugin is run in a worker process, such as for adding books, then the
        plugin will be initialized for every new worker process.
        
        Perform any plugin specific initialization here, such as extracting
        resources from the plugin ZIP file. The path to the ZIP file is
        available as ``self.plugin_path``.
        
        Note that ``self.site_customization`` is **not** available at this point.
        '''
        
        from calibre.customize.ui import initialize_plugin, _initialized_plugins
        installation_type = getattr(self, 'installation_type', None)
        
        def initializor(plugin):
            if installation_type != None:
                return initialize_plugin(plugin, self.plugin_path, installation_type)
            else:
                return initialize_plugin(plugin, self.plugin_path)
        
        def append_plugin(plugin):
            try:
                p = initializor(plugin)
                _initialized_plugins.append(p)
            except Exception as err:
                print('An error has occurred')
                print(err)
                return err
        
        append_plugin(self.MetadataWriter)
        append_plugin(self.MetadataReader)
    
    
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
            from .config import ConfigWidget
            return ConfigWidget(self.actual_plugin_)
    
    def save_settings(self, config_widget):
        '''
        Save the settings specified by the user with config_widget.
        
        :param config_widget: The widget returned by :meth:`config_widget`.
        '''
        config_widget.save_settings()
    
    
    class MetadataReader(MetadataReaderPlugin):
        '''
        A plugin that implements reading metadata from a set of file types.
        '''
        #: Set of file types for which this plugin should be run.
        #: For example: ``{'lit', 'mobi', 'prc'}``
        file_types = FILES_TYPES
        
        name                    = NAME.READER
        description             = DESCRIPTION.READER
        supported_platforms     = SUPPORTED_PLATFORMS
        author                  = AUTHOR
        version                 = VERSION
        minimum_calibre_version = MINIMUM_CALIBRE_VERSION
        
        
        def get_metadata(self, stream, type):
            '''
            Return metadata for the file represented by stream (a file like object
            that supports reading). Raise an exception when there is an error
            with the input data.
            
            :param type: The type of file. Guaranteed to be one of the entries
                in :attr:`file_types`.
            :return: A :class:`calibre.ebooks.metadata.book.Metadata` object
            '''
            from .action import read_metadata
            return read_metadata(stream, type)
        
        def is_customizable(self):
            '''
            This method must return True to enable customization via
            Preferences->Plugins
            '''
            return True
        
        def config_widget(self):
            from calibre.customize.ui import find_plugin
            p = find_plugin(ePubExtendedMetadata.name)
            if p and hasattr(p, 'actual_plugin_'):
                from .config import ConfigReaderWidget
                return ConfigReaderWidget(p.actual_plugin_)
    
        def save_settings(self, config_widget):
            config_widget.save_settings()
    
    
    class MetadataWriter(MetadataWriterPlugin):
        '''
        A plugin that implements reading metadata from a set of file types.
        '''
        #: Set of file types for which this plugin should be run.
        #: For example: ``{'lit', 'mobi', 'prc'}``
        file_types = FILES_TYPES
        
        name                    = NAME.WRITER
        description             = DESCRIPTION.WRITER
        supported_platforms     = SUPPORTED_PLATFORMS
        author                  = AUTHOR
        version                 = VERSION
        minimum_calibre_version = MINIMUM_CALIBRE_VERSION
        
        def set_metadata(self, stream, mi, type):
            '''
            Set metadata for the file represented by stream (a file like object
            that supports reading). Raise an exception when there is an error
            with the input data.
            
            :param type: The type of file. Guaranteed to be one of the entries
                in :attr:`file_types`.
            :param mi: A :class:`calibre.ebooks.metadata.book.Metadata` object
            '''
            from .action import write_metadata
            write_metadata(stream, mi, type)



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
