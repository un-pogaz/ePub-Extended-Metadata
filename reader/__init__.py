#!/usr/bin/env python

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'


# The class that all Interface Action plugin wrappers must inherit from
from calibre.customize import MetadataReaderPlugin, MetadataWriterPlugin


PLUGIN_CLASSE = None
def get_plugin_attribut(name, default=None):
    """Retrieve a attribut on the main plugin class"""
    
    global PLUGIN_CLASSE
    if not PLUGIN_CLASSE:
        import importlib
        from calibre.customize import Plugin
        #Yes, it's very long for a one line. It's seems crazy, but it's fun and it works
        plugin_classes = [ obj for obj in importlib.import_module('.'.join(__name__.split('.')[:-1])).__dict__.values() if isinstance(obj, type) and issubclass(obj, Plugin) and obj.name != 'Trivial Plugin' ]
        
        plugin_classes.sort(key=lambda c:(getattr(c, '__module__', None) or '').count('.'))
        PLUGIN_CLASSE = plugin_classes[0]
    
    return getattr(PLUGIN_CLASSE, name, default)


class MetadataReader(MetadataReaderPlugin):
    '''
    A plugin that implements reading metadata from a set of file types.
    '''
    #: Set of file types for which this plugin should be run.
    #: For example: ``{'lit', 'mobi', 'prc'}``
    file_types = get_plugin_attribut('file_types')
    
    name                    = get_plugin_attribut('name_reader')
    description             = get_plugin_attribut('description_reader')
    supported_platforms     = get_plugin_attribut('supported_platforms')
    author                  = get_plugin_attribut('author')
    version                 = get_plugin_attribut('version')
    minimum_calibre_version = get_plugin_attribut('minimum_calibre_version')
    
    def get_metadata(self, stream, type):
        '''
        Return metadata for the file represented by stream (a file like object
        that supports reading). Raise an exception when there is an error
        with the input data.
        
        :param type: The type of file. Guaranteed to be one of the entries
            in :attr:`file_types`.
        :return: A :class:`calibre.ebooks.metadata.book.Metadata` object
        '''
        from calibre.customize.builtins import EPUBMetadataReader
        from calibre.customize.ui import find_plugin, quick_metadata
        
        # Use the Calibre EPUBMetadataReader
        if hasattr(stream, 'seek'): stream.seek(0)
        calibre_reader = find_plugin(EPUBMetadataReader.name)
        calibre_reader.quick = quick_metadata.quick
        mi = calibre_reader.get_metadata(stream, type)
        
        if find_plugin(get_plugin_attribut('name')):
            if hasattr(stream, 'seek'): stream.seek(0)
            from ..action import read_metadata
            return read_metadata(stream, type, mi)
        else:
            return mi
    
    def is_customizable(self):
        '''
        This method must return True to enable customization via
        Preferences->Plugins
        '''
        return True
    
    def config_widget(self):
        from ..config import ConfigReaderWidget
        return ConfigReaderWidget()
    
    def save_settings(self, config_widget):
        config_widget.save_settings()
