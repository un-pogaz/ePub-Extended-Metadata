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

from lxml import etree

from calibre import prints
from calibre.constants import numeric_version as calibre_version
from calibre.gui2 import error_dialog, warning_dialog, question_dialog, info_dialog

from calibre_plugins.epub_contributors_metadata.common_utils import debug_print
from calibre_plugins.epub_contributors_metadata.container import ContainerOpfStream, NAMESPACES



def read_contributors(epub_path):
    contributors = {}
    
    # Use a "stream" to read the OPF without any extracting
    with ContainerOpfStream(epub_path) as container:
        contributors = _read_contributors(container)
    
    return contributors

def write_contributors(epub_path, contributors):
    debug_print('write_contributors()')
    debug_print('contributors', contributors)
    
    # Use a "stream" to read the OPF without any extracting
    with ContainerOpfStream(epub_path) as container:
        is_modified = _write_contributors(container, contributors)
        
        if is_modified:
            container.save()
    
    return is_modified


def _get_version(container):
    return tuple([ int(i) for i in container.opf.xpath('/opf:package', namespaces=NAMESPACES)[0].get('version', '2.0').split('.')])

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
    is_modified = False
    
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
        
        
        
    
    if version[0] == 3:
        debug_print('version 3')
    
    if is_modified:
        container.write(epub_path)
    
    return is_modified