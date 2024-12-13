#!/usr/bin/env python

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'


# The class that all Interface Action plugin wrappers must inherit from
from calibre.customize import MetadataReaderPlugin


class MetadataReader(MetadataReaderPlugin):
    """
    A plugin that implements reading metadata from a set of file types.
    """
    # plugin attributs are set during the initialization in ePubExtendedMetadata
    
    def get_metadata(self, stream, type):
        """
        Return metadata for the file represented by stream (a file like object
        that supports reading). Raise an exception when there is an error
        with the input data.
        
        :param type: The type of file. Guaranteed to be one of the entries
            in :attr:`file_types`.
        :return: A :class:`calibre.ebooks.metadata.book.Metadata` object
        """
        from calibre.customize.builtins import EPUBMetadataReader
        from calibre.customize.ui import find_plugin, quick_metadata
        
        from ..common_utils import get_plugin_attribut
        
        # Use the Calibre EPUBMetadataReader
        if hasattr(stream, 'seek'):
            stream.seek(0)
        calibre_reader = find_plugin(EPUBMetadataReader.name)
        calibre_reader.quick = quick_metadata.quick
        mi = calibre_reader.get_metadata(stream, type)
        
        if find_plugin(get_plugin_attribut('name')):
            if hasattr(stream, 'seek'):
                stream.seek(0)
            from ..action import read_metadata
            return read_metadata(stream, type, mi)
        else:
            return mi
    
    def is_customizable(self):
        """
        This method must return True to enable customization via
        Preferences->Plugins
        """
        return True
    
    def config_widget(self):
        from ..config import ConfigReaderWidget
        return ConfigReaderWidget()
    
    def save_settings(self, config_widget):
        config_widget.save_settings()
