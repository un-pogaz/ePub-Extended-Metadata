#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'
__docformat__ = 'restructuredtext en'


# The class that all Interface Action plugin wrappers must inherit from
from calibre.customize import MetadataReaderPlugin, MetadataWriterPlugin

def get__init__attribut(name, default=None, use_root_has_default=False):
    ns = __name__.split('.')
    ns.pop(-1)
    
    if use_root_has_default:
        default = ns[-1]
    
    import importlib
    return getattr(importlib.import_module('.'.join(ns)), name, default)

INFO = get__init__attribut('INFO')

class MetadataWriter(MetadataWriterPlugin):
    '''
    A plugin that implements reading metadata from a set of file types.
    '''
    #: Set of file types for which this plugin should be run.
    #: For example: ``{'lit', 'mobi', 'prc'}``
    file_types = INFO.FILES_TYPES
    
    name                    = INFO.WRITER
    description             = INFO.DESCRIPTION_WRITER
    supported_platforms     = INFO.SUPPORTED_PLATFORMS
    author                  = INFO.AUTHOR
    version                 = INFO.VERSION
    minimum_calibre_version = INFO.MINIMUM_CALIBRE_VERSION
    
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
        from calibre.customize.ui import find_plugin, apply_null_metadata, force_identifiers, config
        
        # Use the Calibre EPUBMetadataWriter
        if hasattr(stream, 'seek'): stream.seek(0)
        calibre_writer = find_plugin(EPUBMetadataWriter.name)
        calibre_writer.apply_null = apply_null_metadata.apply_null
        calibre_writer.force_identifiers = force_identifiers.force_identifiers
        calibre_writer.site_customization = config['plugin_customization'].get(calibre_writer.name, '')
        calibre_writer.set_metadata(stream, mi, type)
        
        if find_plugin(INFO.NAME):
            if hasattr(stream, 'seek'): stream.seek(0)
            from calibre_plugins.epub_extended_metadata.action import write_metadata
            write_metadata(stream, type, mi)
    
    def is_customizable(self):
        '''
        This method must return True to enable customization via
        Preferences->Plugins
        '''
        return True
    
    def config_widget(self):
        from calibre.customize.ui import find_plugin
        return find_plugin(INFO.NAME).config_widget()