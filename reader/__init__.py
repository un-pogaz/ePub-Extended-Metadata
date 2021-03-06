#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'
__docformat__ = 'restructuredtext en'


# The class that all Interface Action plugin wrappers must inherit from
from calibre.customize import MetadataReaderPlugin, MetadataWriterPlugin

from ..common import *

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
        from calibre.customize.builtins import EPUBMetadataReader
        from calibre.customize.ui import find_plugin, quick_metadata
        
        # Use the Calibre EPUBMetadataReader
        if hasattr(stream, 'seek'): stream.seek(0)
        calibre_reader = find_plugin(EPUBMetadataReader.name)
        calibre_reader.quick = quick_metadata.quick
        mi = calibre_reader.get_metadata(stream, type)
        
        if find_plugin(NAME.BASE):
            if hasattr(stream, 'seek'): stream.seek(0)
            from calibre_plugins.epub_extended_metadata.action import read_metadata
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
        from calibre.customize.ui import find_plugin
        from ..config import ConfigReaderWidget
        return ConfigReaderWidget(find_plugin(NAME.BASE).actual_plugin_)
    
    def save_settings(self, config_widget):
        config_widget.save_settings()

