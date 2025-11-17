#!/usr/bin/env python

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'


try:
    load_translations()
except NameError:
    pass  # load_translations() added in calibre 1.9

import os
from collections import defaultdict

from lxml import etree

from calibre.ebooks.metadata import author_to_author_sort, string_to_authors, title_sort
from calibre.ebooks.metadata.epub import EPubException, get_zip_reader
from calibre.ebooks.metadata.opf2 import OPF
from calibre.ebooks.metadata.opf3 import (
    find_main_title,
    find_subtitle,
    normalize_whitespace,
    properties_for_id,
    read_prefixes,
    read_refines,
    read_title,
)
from calibre.ebooks.metadata.utils import pretty_print_opf
from calibre.utils.zipfile import ZIP_DEFLATED, ZipFile, safe_replace

from .common_utils import debug_print
from .config import FIELD, KEY

NS_OCF = 'urn:oasis:names:tc:opendocument:xmlns:container'
NS_OPF = 'http://www.idpf.org/2007/opf'
NS_DC = 'http://purl.org/dc/elements/1.1/'
NS_NCX = 'http://www.daisy.org/z3986/2005/ncx/'

NAMESPACES={'opf':NS_OPF, 'dc':NS_DC, 'ocf':NS_OCF, 'ncx':NS_NCX}


class ParseError(ValueError):
    def __init__(self, name, err):
        self.name = name
        self.err = err
        ValueError.__init__(self, f'Failed to parse: {name} with error: {err}')


class OPFException(EPubException):
    pass


class OPFParseError(OPFException, ParseError):
    def __init__(self, name, err):
        ValueError.__init__(self, name, err)


class ContainerExtendedMetadata:
    '''
    epub can be a file path or a stream
    '''
    def __init__(self, epub, read_only=False):
        # Load ZIP
        self.ZIP = None
        self.reader = None
        self._opf = None
        
        self.ZIP = ZipFile(epub, mode='r' if read_only else 'a', compression=ZIP_DEFLATED)
        self.reader = get_zip_reader(self.ZIP.fp, root=os.getcwd())
        self._opf = self.reader.opf
            
        import math
        d, i = math.modf(self.opf.package_version)
        self._version = (int(i), int(d))
    
    @property
    def opf(self):
        return self._opf
    
    @property
    def root(self):
        return self._opf.root
    
    @property
    def metadata(self):
        return self.opf.metadata
    
    @property
    def languages(self):
        return self.opf.languages
    
    @property
    def version(self):
        return self._version
    
    def __enter__(self):
        return self
    
    def save_opf(self):
        pretty_print_opf(self.opf.root)
        xml_opf = etree.tostring(self.opf.root, encoding='UTF-8', pretty_print=True)
        
        if self.reader:
            if isinstance(xml_opf, bytes):
                safe_replace(self.ZIP.fp, self.reader.container[OPF.MIMETYPE], xml_opf)
            else:
                safe_replace(self.ZIP.fp, self.reader.container[OPF.MIMETYPE], xml_opf.encode('utf-8'))
    
    def __exit__(self, type, value, traceback):
        self.close()
    
    def __del__(self):
        self.close()
    
    def close(self):
        self.ZIP.close()


def default_extended_metadata():
    rslt = {}
    rslt[KEY.CREATORS] = []
    rslt[KEY.CONTRIBUTORS] = defaultdict(list)
    rslt[KEY.TITLES] = {}
    return rslt


def find_title_role(root, refines, role):
    for title in root.xpath('./opf:metadata/dc:title', namespaces=NAMESPACES):
        if not title.text or not title.text.strip():
            continue
        props = properties_for_id(title.get('id'), refines)
        if props.get('title-type') == role:
            return title


def read_extended_metadata(epub):
    '''
    epub/opf can be a file path or a stream
    '''
    extended_metadata = default_extended_metadata()
    
    # Use a "stream" to read the OPF without any extracting
    with ContainerExtendedMetadata(epub, read_only=True) as container:
        extended_metadata = _read_extended_metadata(container)
    
    return extended_metadata


def write_extended_metadata(epub, extended_metadata):
    '''
    epub/opf can be a file path or a stream
    '''
    debug_print('write_extended_metadata()')
    debug_print('extended_metadata:', extended_metadata)
    
    # Use a "stream" to read the OPF without any extracting
    with ContainerExtendedMetadata(epub, read_only=False) as container:
        _write_extended_metadata(container, extended_metadata)
        container.save_opf()


def _read_extended_metadata(container):
    extended_metadata = default_extended_metadata()
    contributors = extended_metadata[KEY.CONTRIBUTORS]
    titles = extended_metadata[KEY.TITLES]
    
    if not container.opf:
        return extended_metadata
    
    def contributors_append(role, author):
        # we cannot use set because we want to keep the ordre
        if author not in contributors[role]:
            contributors[role].append(author)
    
    tag_role = (
        ('dc:creator', 'aut'),
        ('dc:contributor', 'oth'),
    )
    if container.version[0] == 2:
        for tag, drole in tag_role:
            for child in container.metadata.xpath(tag, namespaces=NAMESPACES):
                tbl = child.xpath('@opf:role', namespaces=NAMESPACES)
                role = tbl[0] if tbl else drole
                role = role.strip() or drole
                for author in string_to_authors(child.text):
                    contributors_append(role, author)
    
    if container.version[0] == 3:
        for tag, drole in tag_role:
            for child in container.metadata.xpath(f'{tag}[@id]', namespaces=NAMESPACES):
                id = child.attrib['id']
                xpath = f'opf:meta[@refines="#{id}" and @property="role" and @scheme="marc:relators"]'
                roles = container.metadata.xpath(xpath, namespaces=NAMESPACES)
                
                roles = [r.text.strip() or drole for r in roles]
                if not roles:
                    roles = [drole]
                
                for author in string_to_authors(child.text):
                    for role in roles:
                        contributors_append(role, author)
            
            for child in container.metadata.xpath(f'{tag}[not(@id)]', namespaces=NAMESPACES):
                for author in string_to_authors(child.text):
                    contributors_append(role, author)
        
        ## titles
        prefixes, refines = read_prefixes(container.root), read_refines(container.root)
        def to_text(node):
            if node is None:
                return None
            return normalize_whitespace(node.text.strip())
        
        xpath = 'opf:meta[@refines and @property="title-type"]'
        roles = container.metadata.xpath(xpath, namespaces=NAMESPACES)
        roles = {r.text.strip() or drole for r in roles}
        for role in roles:
            titles[role] = to_text(find_title_role(container.root, refines, role))
        
        titles[FIELD.TITLES.MAIN] = to_text(find_main_title(container.root, refines))
        titles[FIELD.TITLES.SUBTITLE] = to_text(find_subtitle(container.root, refines))
        titles[FIELD.TITLES.READ] = read_title(container.root, prefixes, refines)
    
    debug_print('extended_metadata:', extended_metadata)
    
    return extended_metadata


def _write_extended_metadata(container, extended_metadata):
    if not container.opf:
        return False
    
    epub_extended_metadata = _read_extended_metadata(container)
    
    # remove internal values
    for role in list(epub_extended_metadata[KEY.TITLES].keys()):
        if role.startswith(':') or role == FIELD.TITLES.MAIN:
            epub_extended_metadata[KEY.TITLES].pop(role, None)
    
    # merge source metadata and the new
    for role, value in extended_metadata[KEY.CONTRIBUTORS].items():
        epub_extended_metadata[KEY.CONTRIBUTORS][role] = value
    for role, value in extended_metadata[KEY.TITLES].items():
        epub_extended_metadata[KEY.TITLES][role] = value
    
    def get_index(tag):
        tags = container.metadata.xpath(f'dc:{tag}', namespaces=NAMESPACES)
        if tags:
            return container.metadata.index(tags[-1])+1
        return 0
    
    if container.version[0] == 2:
        idx = get_index('creator')
        for role in sorted(epub_extended_metadata[KEY.CONTRIBUTORS].keys()):
            for meta in container.metadata.xpath(f'dc:contributor[@opf:role="{role}"]', namespaces=NAMESPACES):
                container.metadata.remove(meta)
            for contrib in epub_extended_metadata[KEY.CONTRIBUTORS][role]:
                element = etree.Element(etree.QName(NS_DC, 'contributor'))
                element.text = contrib
                element.attrib[etree.QName(NS_OPF, 'role')] = role
                element.attrib[etree.QName(NS_OPF, 'file-as')] = author_to_author_sort(contrib)
                container.metadata.insert(idx, element)
                idx = idx+1
    
    if container.version[0] == 3:
        ## titles
        for title in container.metadata.xpath('dc:title', namespaces=NAMESPACES):
            id_s = title.attrib.get('id')
            if id_s:
                is_main = False
                xpath = f'opf:meta[@refines="#{id_s}" and @property="title-type"]'
                for meta in container.metadata.xpath(xpath, namespaces=NAMESPACES):
                    if meta.text == FIELD.TITLES.MAIN:
                        is_main = True
                    else:
                        container.metadata.remove(meta)
                if is_main:
                    continue
                # if the title has others meta linked (except "file-as")
                xpath = f'opf:meta[@refines="#{id_s}" and not(@property="file-as")]'
                if not container.metadata.xpath(xpath, namespaces=NAMESPACES):
                    # if the title has no others meta linked (or only "file-as"), del the title
                    container.metadata.remove(title)
                    # and del the "file-as"
                    for meta in container.metadata.xpath(f'opf:meta[@refines="#{id_s}"]', namespaces=NAMESPACES):
                        container.metadata.remove(meta)
        
        idx = get_index('title')
        title_id = {}
        if container.languages:
            lang = container.languages[0]
        else:
            lang = None
        
        for role, title in sorted(epub_extended_metadata[KEY.TITLES].items()):
            if not title:
                continue
            element = etree.Element(etree.QName(NS_DC, 'title'))
            element.text = title
            id_s = f'title-{role}'
            element.attrib['id'] = id_s
            container.metadata.insert(idx, element)
            idx = idx+1
            
            title_id[role] = id_s
            
            file = etree.Element('meta')
            file.text = title_sort(title, lang=lang)
            file.attrib['refines'] = f'#{id_s}'
            file.attrib['property'] = 'file-as'
            container.metadata.insert(idx, file)
            idx = idx+1
        
        for role, id_s in sorted(title_id.items()):
            meta = etree.Element('meta')
            meta.text = role
            meta.attrib['refines'] = f'#{id_s}'
            meta.attrib['property'] = 'title-type'
            container.metadata.insert(idx, meta)
            idx = idx+1
        
        ## contributors
        for contrib in container.metadata.xpath('dc:contributor', namespaces=NAMESPACES):
            id_s = contrib.attrib.get('id')
            if id_s:
                # remove all marc code
                xpath = f'opf:meta[@refines="#{id_s}" and @property="role" and @scheme="marc:relators"]'
                for meta in container.metadata.xpath(xpath, namespaces=NAMESPACES):
                    container.metadata.remove(meta)
                # if the contributor has others meta linked (except "file-as")
                xpath = f'opf:meta[@refines="#{id_s}" and not(@property="file-as")]'
                if not container.metadata.xpath(xpath, namespaces=NAMESPACES):
                    # if the contributor has no others meta linked (or only "file-as"), del the contributor
                    container.metadata.remove(contrib)
                    # and del the "file-as"
                    for meta in container.metadata.xpath(f'opf:meta[@refines="#{id_s}"]', namespaces=NAMESPACES):
                        container.metadata.remove(meta)
            else:
                # remove contributor without id
                container.metadata.remove(contrib)
        
        idx = get_index('creator')
        role_id = defaultdict(list)
        
        for role in sorted(epub_extended_metadata[KEY.CONTRIBUTORS].keys()):
            id_n = (len(role_id[role]) if role in role_id else 0) + 1
            
            for contrib in epub_extended_metadata[KEY.CONTRIBUTORS][role]:
                element = etree.Element(etree.QName(NS_DC, 'contributor'))
                element.text = contrib
                id_s = role+f'-{id_n:02d}'
                element.attrib['id'] = id_s
                container.metadata.insert(idx, element)
                idx = idx+1
                
                role_id[role].append(id_s)
                
                file = etree.Element('meta')
                file.text = author_to_author_sort(contrib)
                file.attrib['refines'] = f'#{id_s}'
                file.attrib['property'] = 'file-as'
                container.metadata.insert(idx, file)
                idx = idx+1
                
                id_n = id_n+1
        
        for role in sorted(role_id.keys()):
            for id_s in role_id[role]:
                meta = etree.Element('meta')
                meta.text = role
                meta.attrib['refines'] = f'#{id_s}'
                meta.attrib['property'] = 'role'
                meta.attrib['scheme'] = 'marc:relators'
                container.metadata.insert(idx, meta)
                idx = idx+1
