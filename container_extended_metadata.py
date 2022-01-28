#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'
__docformat__ = 'restructuredtext en'

import copy, time, os
# python3 compatibility
from six.moves import range
from six import text_type as unicode

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from datetime import datetime
from collections import defaultdict
from functools import partial
from polyglot.builtins import iteritems, itervalues

from lxml import etree
from lxml.etree import XMLSyntaxError
from six.moves.urllib.parse import urldefrag, urlparse, urlunparse
from six.moves.urllib.parse import unquote as urlunquote

from calibre import prints
from calibre.ebooks.chardet import xml_to_unicode
from calibre.ebooks.metadata.opf2 import OPF
import calibre.ebooks.metadata.opf3 as opf3
from calibre.ebooks.metadata.epub import get_zip_reader, EPubException, OCFException, ContainerException
from calibre.ebooks.oeb.parse_utils import RECOVER_PARSER
from calibre.utils.zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED, safe_replace
from polyglot.builtins import iteritems, itervalues

from .common_utils import debug_print, equals_no_case
from .config import KEY


NS_OCF = 'urn:oasis:names:tc:opendocument:xmlns:container'
NS_OPF = 'http://www.idpf.org/2007/opf'
NS_DC = 'http://purl.org/dc/elements/1.1/'
NS_NCX = 'http://www.daisy.org/z3986/2005/ncx/'

NAMESPACES={'opf':NS_OPF, 'dc':NS_DC, 'ocf':NS_OCF, 'ncx':NS_NCX}


class ParseError(ValueError):
    def __init__(self, name, err):
        self.name = name
        self.err = err
        ValueError.__init__(self, 'Failed to parse: {:s} with error: {:s}'.format(name, err))

class OPFException(EPubException):
    pass

class OPFParseError(OPFException, ParseError):
    def __init__(self, name, err):
        ValueError.__init__(self, name, err)


class Container_ePub(object):
    '''
    epub can be a file path or a stream
    '''
    def __init__(self, epub, read_only=False):
        # Load ZIP
        self.ZIP = ZipFile(epub, mode='r' if read_only else 'a', compression=ZIP_DEFLATED)
        self.path = getattr(self.ZIP, 'filename', None)
        self.reader = get_zip_reader(self.ZIP.fp, root=os.getcwd())
        
        import math
        d, i = math.modf(self.reader.opf.package_version)
        self._version = (int(i), int(d))
        self._opf = self.reader.opf
        
        self._metadata = self.reader.opf.metadata
    
    
    @property
    def opf(self):
        return self._opf
    @property
    def metadata(self):
        return self._metadata
    @property
    def version(self):
        return self._version
    @property
    def opf_name(self):
        return self.reader.container[OPF.MIMETYPE]
    
    def __enter__(self):
        return self
    
    def get_zip_entry(self, name):
        for entry in self.ZIP.namelist():
            if equals_no_case(entry, name):
                return entry
    
    
    def save_opf(self):
        debug_print('save()')
        if self.opf_name:
            xml_opf = etree.tostring(self.opf.root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
            safe_replace(self.ZIP.fp, self.opf_name, xml_opf.encode('utf-8'))
    
    def __exit__(self, type, value, traceback):
        self.close()
    
    def __del__(self):
        self.close()
    
    def close(self):
        self.ZIP.close()


def read_extended_metadata(epub):
    '''
    epub can be a file path or a stream
    '''
    extended_metadata = {}
    
    # Use a "stream" to read the OPF without any extracting
    with Container_ePub(epub, read_only=True) as container:
        extended_metadata = _read_extended_metadata(container)
    
    return extended_metadata

def write_extended_metadata(epub, extended_metadata):
    '''
    epub can be a file path or a stream
    '''
    debug_print('write_extended_metadata()')
    debug_print('extended_metadata', extended_metadata)
    
    # Use a "stream" to read the OPF without any extracting
    with Container_ePub(epub) as container:
        is_modified = _write_extended_metadata(container, extended_metadata)
        if is_modified:
            container.save_opf()
    
    return is_modified


def _read_extended_metadata(container):
    extended_metadata = {}
    extended_metadata[KEY.CONTRIBUTORS] = contributors = {}
    if not container.opf_name:
        return extended_metadata
    
    if container.version[0] == 2:
        for child in container.metadata.xpath('dc:contributor[@opf:role]', namespaces=NAMESPACES):
            role = child.xpath('@opf:role', namespaces=NAMESPACES)[0]
            if not role in contributors:
                contributors[role] = []
            contributors[role].append(child.text)
            
            
        
        
        
        
    
    if container.version[0] == 3:
        debug_print('version 3')
    
    return extended_metadata

def _write_contributors(container, extended_metadata):
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
    
    
    write_extended_metadata = {}
    is_modified = False
    
    if container.version[0] == 2:
        
        ## name="calibre:user_metadata
        
        for child in container.metadata:
            debug_print('child', child)
            debug_print('child.text', child.text)
            debug_print('child.attrib', child.attrib)
            
            #to_remove.append(child)
        
        if to_remove:
            for node in to_remove:
                metadata.remove(node)
        
        
        
    
    if container.version[0] == 3:
        debug_print('version 3')
    
    return True