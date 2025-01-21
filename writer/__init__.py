#!/usr/bin/env python

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'


# The class that all Interface Action plugin wrappers must inherit from
from calibre.customize import MetadataWriterPlugin


class MetadataWriter(MetadataWriterPlugin):
    '''
    A plugin that implements reading metadata from a set of file types.
    '''
    # plugin attributs are set during the initialization in ePubExtendedMetadata
    
    def set_metadata(self, stream, mi, type):
        '''
        Set metadata for the file represented by stream (a file like object
        that supports reading). Raise an exception when there is an error
        with the input data.
        
        :param type: The type of file. Guaranteed to be one of the entries
            in :attr:`file_types`.
        :param mi: A :class:`calibre.ebooks.metadata.book.Metadata` object
        '''
        from calibre.customize.builtins import EPUBMetadataWriter
        from calibre.customize.ui import apply_null_metadata, config, find_plugin, force_identifiers
        
        from ..common_utils import get_plugin_attribut
        
        # Use the Calibre EPUBMetadataWriter
        if hasattr(stream, 'seek'):
            stream.seek(0)
        calibre_writer = find_plugin(EPUBMetadataWriter.name)
        calibre_writer.apply_null = apply_null_metadata.apply_null
        calibre_writer.force_identifiers = force_identifiers.force_identifiers
        calibre_writer.site_customization = config['plugin_customization'].get(calibre_writer.name, '')
        calibre_writer.set_metadata(stream, mi, type)
        
        if find_plugin(get_plugin_attribut('name')):
            if hasattr(stream, 'seek'):
                stream.seek(0)
            from ..action import write_metadata
            write_metadata(stream, type, mi)
    
    def is_customizable(self):
        '''
        This method must return True to enable customization via
        Preferences->Plugins
        '''
        return True
    
    def config_widget(self):
        from calibre.customize.ui import find_plugin
        
        from ..common_utils import get_plugin_attribut
        return find_plugin(get_plugin_attribut('name')).config_widget()
    
    def save_settings(self, config_widget):
        config_widget.save_settings()
