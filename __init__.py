#!/usr/bin/env python

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'


try:
    load_translations()
except NameError:
    pass  # load_translations() added in calibre 1.9

# The class that all Interface Action plugin wrappers must inherit from
from calibre.customize import InterfaceActionBase


class ePubExtendedMetadata(InterfaceActionBase):
    '''
    This class is a simple wrapper that provides information about the actual
    plugin class. The actual interface plugin class is called InterfacePlugin
    and is defined in the ui.py file, as specified in the actual_plugin field
    below.
    
    The reason for having two classes is that it allows the command line
    calibre utilities to run without needing to load the GUI libraries.
    '''
    name                    = 'ePub Extended Metadata'
    description             = _("Read and write a wider range of metadata for ePub's files "
                                "and associating them to columns in your libraries.")
    supported_platforms     = ['windows', 'osx', 'linux']
    author                  = 'un_pogaz'
    version                 = (0, 13, 0)
    minimum_calibre_version = (5, 0, 0)
    
    name_reader              = name + ' {Reader}'
    name_writer              = name + ' {Writer}'
    file_types = {'epub'}
    description_companion           = '\n' +_('This is an companion (and embeded) plugin of "{:s}".').format(name)
    description_reader              = _('Read a wider range of metadata from the ePub file.') + description_companion
    description_writer              = _('Write a wider range of metadata in the ePub file.') + description_companion
    
    # This field defines the GUI plugin class that contains all the code
    # that actually does something. Its format is module_path:class_name
    # The specified class must be defined in the specified module.
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
        
        from .reader import MetadataReader
        from .writer import MetadataWriter
        
        self.initialize_embedded_plugin(MetadataReader, name=self.name_reader, description=self.description_reader)
        self.initialize_embedded_plugin(MetadataWriter, name=self.name_writer, description=self.description_writer)
    
    def initialize_embedded_plugin(self, plugin, name: str=None, description: str=None):
        '''
        A Calibre plugin can normally only contain one Plugin class.
        In our case, this would be the file type class.
        However, we want to load the GUI plugin, too, so we have to trick
        Calibre into believing that there's actually a 2nd plugin.
        '''
        
        from calibre.customize.ui import _initialized_plugins, initialize_plugin
        
        for p in _initialized_plugins:
            if isinstance(p, plugin):
                return p
        
        plugin.name = name or str(plugin.__name__)
        plugin.description = description or self.description
        
        plugin.version = self.version
        plugin.minimum_calibre_version = self.minimum_calibre_version
        plugin.supported_platforms = self.supported_platforms
        plugin.author = self.author
        
        plugin.file_types = getattr(self, 'file_types', None)
        
        installation_type = getattr(self, 'installation_type', None)
        
        try:
            if installation_type is not None:
                p = initialize_plugin(plugin, self.plugin_path, installation_type)
            else:
                p = initialize_plugin(plugin, self.plugin_path)
            _initialized_plugins.append(p)
            return p
        except Exception as err:
            print(f'{self.name}: Error during the initialize of the embedded plugin "{plugin.name}":\n{err}\n')
            return None
    
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
            return ConfigWidget()
    
    def save_settings(self, config_widget):
        '''
        Save the settings specified by the user with config_widget.
        
        :param config_widget: The widget returned by :meth:`config_widget`.
        '''
        config_widget.save_settings()


# For testing, run from command line with this:
# calibre-debug -e __init__.py
if __name__ == '__main__':
    from calibre.gui2 import Application
    from calibre.gui2.preferences import test_widget
    app = Application([])
    test_widget('Advanced', 'Plugins')
