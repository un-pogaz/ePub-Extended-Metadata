#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'
__docformat__ = 'restructuredtext en'


# The class that all Interface Action plugin wrappers must inherit from
from calibre.customize import MetadataReaderPlugin, MetadataWriterPlugin


def get_plugin_attribut(name, default=None):
        ns = __name__.split('.')
        ns.pop(-1)
        ns = '.'.join(ns)
        import importlib
        m = importlib.import_module(ns)
        
        return getattr(getattr(m, 'ePubExtendedMetadata', None), name, default)

class MetadataWriter(MetadataWriterPlugin):
    '''
    A plugin that implements reading metadata from a set of file types.
    '''
    #: Set of file types for which this plugin should be run.
    #: For example: ``{'lit', 'mobi', 'prc'}``
    file_types = get_plugin_attribut('file_types')
    
    name                    = get_plugin_attribut('name_writer')
    description             = get_plugin_attribut('description_writer')
    supported_platforms     = get_plugin_attribut('supported_platforms')
    author                  = get_plugin_attribut('author')
    version                 = get_plugin_attribut('version')
    minimum_calibre_version = get_plugin_attribut('minimum_calibre_version')
    
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
        
        if find_plugin(get_plugin_attribut('name')):
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
        return find_plugin(get_plugin_attribut('name')).config_widget()