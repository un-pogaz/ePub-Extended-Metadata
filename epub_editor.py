#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'
__docformat__ = 'restructuredtext en'

import os, time, copy
# calibre Python 3 compatibility.
from six import text_type as unicode

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from functools import partial
from datetime import datetime
from collections import defaultdict


from calibre import prints
from calibre.constants import numeric_version as calibre_version
from calibre.gui2 import error_dialog, warning_dialog, question_dialog, info_dialog
from polyglot.builtins import iteritems

from calibre_plugins.edit_contributors_metadata.common_utils import debug_print

from lxml import etree
from calibre import CurrentDir
from calibre.libunzip import extract as zipextract
from calibre.ptempfile import TemporaryDirectory
from calibre.utils.logging import Log
from calibre_plugins.edit_contributors_metadata.container import ExtendedContainer, NS_OPF, NS_DC

class FakeLog(object):

    def __init__(self, level=None):
        pass

    def prints(self, level, *args, **kwargs):
        pass

    def print_with_flush(self, level, *args, **kwargs):
        pass

    def exception(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        pass

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass

    def flush(self):
        pass

    def close(self):
        pass


NAMESPACES={'opf':NS_OPF, 'dc':NS_DC}

def _get_version(container):
    return tuple([ int(i) for i in container.opf.xpath('/opf:package', namespaces=NAMESPACES)[0].get('version', '2.0').split('.')])

def read_contributors(epub_path):
    contributors = {}
    # Extract the epub into a temp directory
    with TemporaryDirectory('_edit-contributors') as tdir:
        with CurrentDir(tdir):
            zipextract(epub_path, tdir)
            
            # Use our own simplified wrapper around an ePub that will
            # preserve the file structure and css
            container = ExtendedContainer(tdir, FakeLog())
            contributors = _read_contributors(container)
    
    return contributors

def _read_contributors(container):
    if not container.opf_name:
        return {}
    
    contributors = {}
    
    version = _get_version(container)
    
    if version[0] == 2:
        for child in container.opf.xpath('//opf:metadata/dc:contributor[@opf:role]', namespaces=NAMESPACES):
            role = child.xpath('@opf:role', namespaces=NAMESPACES)[0]
            if not role in contributors:
                contributors[role] = []
            
            contributors[role].append(child.text)
    
    if version[0] == 3:
        debug_print('version 3')
    
    return contributors


def write_contributors(epub_path, contributors):
    debug_print('write_contributors()')
    debug_print('contributors', contributors)
    
    # Extract the epub into a temp directory
    with TemporaryDirectory('_edit-contributors') as tdir:
        with CurrentDir(tdir):
            zipextract(epub_path, tdir)
            
            # Use our own simplified wrapper around an ePub that will
            # preserve the file structure and css
            container = ExtendedContainer(tdir, FakeLog())
            is_modified = _write_contributors(container, contributors)
    
    return is_modified

def _write_contributors(container, contributors):
    if not container.opf_name:
        return False
    to_remove = []
    
    ################
    #You need to create sub-elements:
    ################
    root = etree.Element("p")
    root.text = 'some'
    
    bold = etree.SubElement(root, 'bold')
    bold.text = 'text'
    
    version = _get_version(container)
    
    metadata = container.opf.xpath('//opf:metadata', namespaces=NAMESPACES)[0]
    
    read_contributors = _read_contributors(container)
    debug_print('read_contributors', read_contributors)
    
    write_contributors = {}
    
    if version[0] == 2:
        
        
        for child in metadata.xpath('dc:contributor[@opf:role]', namespaces=NAMESPACES):
            debug_print('child', child)
            debug_print('child.text', child.text)
            debug_print('child.attrib', child.attrib)
            
            #to_remove.append(child)
        
        if to_remove:
            for node in to_remove:
                metadata.remove(node)
            container.set(container.opf_name, container.opf)
        
        is_modified = False # bool(to_remove)
    
    if version[0] == 3:
        debug_print('version 3')
    
    if is_modified:
        container.write(epub_path)
    
    return is_modified