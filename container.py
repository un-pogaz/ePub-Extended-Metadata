#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (division, absolute_import,
                        print_function)
import six
from six.moves import range
from polyglot.builtins import unicode_type, is_py3

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake <grant.drake@gmail.com>'
__docformat__ = 'restructuredtext en'

import os, posixpath, sys, re
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error

from lxml import etree
from lxml.etree import XMLSyntaxError
from six.moves.urllib.parse import urldefrag, urlparse, urlunparse
from six.moves.urllib.parse import unquote as urlunquote

from calibre import guess_type, prepare_string_for_xml
from calibre.ebooks.chardet import xml_to_unicode
from calibre.ebooks.oeb.parse_utils import RECOVER_PARSER
from calibre.utils.zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

from calibre_plugins.epub_contributors_metadata.common_utils import debug_print, equals_no_case


NS_OCF = 'urn:oasis:names:tc:opendocument:xmlns:container'
NS_OPF = 'http://www.idpf.org/2007/opf'
NS_DC = 'http://purl.org/dc/elements/1.1/'
NS_NCX = 'http://www.daisy.org/z3986/2005/ncx/'

NAMESPACES={'opf':NS_OPF, 'dc':NS_DC, 'ocf':NS_OCF, 'ncx':NS_NCX}


class InvalidEpub(ValueError):
    pass

class ParseError(InvalidEpub):
    def __init__(self, name, err):
        self.name = name
        self.err = err
        InvalidEpub.__init__(self, 'Failed to parse: {:s} with error: {:s}'.format(name, err))


class ContainerOpfStream(object):
    def __init__(self, epub_path):
        self.path = os.path.abspath(epub_path)
        
        self.opf_name = None
        self.opf = None
        self.ZIP = None
        
        # Open ZIP ans load OPF
        self.ZIP = ZipFile(self.path, mode="a", compression=ZIP_DEFLATED)
        
        container_name = self.get_zip_entry('META-INF/container.xml')
        if not container_name:
            raise InvalidEpub('No META-INF/container.xml in epub')
        
        container = etree.fromstring(self.ZIP.read(container_name))
        opf_files = container.xpath(r'/ocf:container/ocf:rootfiles/ocf:rootfile[@media-type="application/oebps-package+xml" and @full-path]', namespaces=NAMESPACES)
        if not opf_files:
            raise InvalidEpub('META-INF/container.xml contains no link to OPF file')
        
        self.opf_name = self.get_zip_entry(opf_files[0].get('full-path'))
        if not self.opf_name:
            raise InvalidEpub('OPF file does not exist at location pointed to by META-INF/container.xml')
        
        if self.opf_name:
            try:
                self.opf = self._parse_xml(self.ZIP.read(self.opf_name))
            except XMLSyntaxError as err:
                name = self.opf_name
                self.opf_name = None
                raise ParseError(name, err)
        
    
    def __enter__(self):
        return self
    
    def get_zip_entry(self, name):
        for entry in self.ZIP.namelist():
            if equals_no_case(entry, name):
                return entry
    
    def _parse_xml(self, data):
        data = xml_to_unicode(data, strip_encoding_pats=True, assume_utf8=True,
                             resolve_entities=True)[0].strip()
        return etree.fromstring(data, parser=RECOVER_PARSER)
    
    
    def save(self):
        debug_print('save()')
        #if self.opf_name:
        #    self.ZIP.delete(self.opf_name)
        #    self.ZIP.writestr(self.opf_name, xml_string)
    
    def __exit__(self, type, value, traceback):
        self.close()
    
    def __del__(self):
        """Call the "close()" method in case the user forgot."""
        self.close()
    
    def close(self):
        self.ZIP.close()
