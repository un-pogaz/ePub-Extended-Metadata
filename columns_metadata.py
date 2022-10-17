#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'
__docformat__ = 'restructuredtext en'

import os, sys, copy, time
# python3 compatibility
from six.moves import range
from six import text_type as unicode

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from datetime import datetime
from collections import defaultdict, OrderedDict
from functools import partial

try: #polyglot added in calibre 4.0
    from polyglot.builtins import iteritems, itervalues
except ImportError:
    def iteritems(d):
        return d.iteritems()
    def itervalues(d):
        return d.itervalues()

from calibre import prints
from calibre.gui2.ui import get_gui
from calibre.library.field_metadata import FieldMetadata

from .common_utils import debug_print, current_db, regex


typeproperty_registry = []
class typeproperty(property):
    def __init__(self, func):
        property.__init__(self, fget=func)
        typeproperty_registry.append(func)


try:
    authors_split_regex = tweaks['authors_split_regex']
    re.compile(authors_split_regex)
except Exception:
    authors_split_regex = r'(?i),?\s+(and|with)\s+'
    """tweaks split regex for authors"""

def string_to_authors(raw_string):
    """
    Split a string into a list of authors
    
    return: list(str)
    """
    from calibre.ebooks.metadata import string_to_authors
    return string_to_authors(raw_string)


def get_columns_from_dict(src_dict, predicate=None):
    """
    Convert a FieldMetadata dict to a ColumnMetadata dict
    
    predicate:
        function with ColumnMetadata as argument to filtre
    
    return: dict(ColumnMetadata)
    """
    def _predicate(column):
        return True
    predicate = predicate or _predicate
    return {cm.name:cm for cm in [ColumnMetadata(fm, k.startswith('#')) for k,fm in iteritems(src_dict) if fm.get('label', None)] if predicate(cm)}

def get_columns_where(predicate=None):
    """
    Get ColumnMetadata of the currend library

    predicate:
        function with ColumnMetadata as argument to filtre
    
    return: dict(ColumnMetadata)
    """
    if current_db():
        return get_columns_from_dict(current_db().field_metadata, predicate)
    else:
        return {}


def _test_is_custom(column, only_custom):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: bool
    """
    if only_custom == True:
        return column.is_custom
    elif only_custom == False:
        return not column.is_custom
    else:
        return True

def get_all_columns(only_custom=None, include_composite=False):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    def predicate(column):
        if not include_composite and column.is_composite:
            return False
        elif include_composite and only_custom == None:
            return True
        else:
            return _test_is_custom(column, only_custom)
    
    return get_columns_where(predicate)

def get_column_from_name(name):
    """Get the column with the specified name, else None
    
    return: ColumnMetadata
    """
    def predicate(column):
        return column.name == name
    for v in itervalues(get_columns_where(predicate)):
        return v
    return None


def _get_columns_type(type, only_custom):
    def predicate(column):
        if type == column.type:
            return _test_is_custom(column, only_custom)
        else:
            return False
    
    return get_columns_where(predicate)

# get type
def get_names(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.names, only_custom)
def get_tags(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.tags, only_custom)
def get_enumeration(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.enumeration, only_custom)
def get_float(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.float, only_custom)
def get_datetime(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.datetime, only_custom)
def get_rating(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.rating, only_custom)
def get_series(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.series, only_custom)
def get_series_index(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.series_index, only_custom)
def get_text(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.text, only_custom)
def get_bool(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.bool, only_custom)
def get_comments(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.comments, only_custom)
def get_html(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.html, only_custom)
def get_markdown(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.markdown, only_custom)
def get_long_text(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.long_text, only_custom)
def get_title(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.title, only_custom)
def get_composite_text(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.composite_text, only_custom)
def get_composite_tag(only_custom=None):
    """
    only_custom:
        True= Only custom
        False= Only default
        None= Both
    
    return: dict(ColumnMetadata)
    """
    return _get_columns_type(ColumnTypes.composite_tag, only_custom)


def get_possible_fields():
    """
    Get the fields of the current library
    
    return: all_fields -> list(str), writable_fields -> list(str)
    """
    def predicate(column):
        if column.name not in ['id' , 'au_map', 'timestamp', 'formats', 'ondevice', 'news', 'series_sort', 'path', 'in_tag_browser'] or column.type:
            return True
        else:
            return False
    
    columns = get_columns_where(predicate)
    
    all_fields = [cc.name for cc in itervalues(columns)]
    all_fields.sort()
    all_fields.insert(0, '{template}')
    writable_fields = [cc.name for cc in itervalues(columns) if not cc.is_composite]
    writable_fields.sort()
    return all_fields, writable_fields

def get_possible_columns():
    """
    Get the name of the columns in the library
    
    return: list(str)
    """
    standard = ['title', 'authors', 'tags', 'series', 'publisher', 'pubdate', 'rating', 'languages', 'last_modified', 'timestamp', 'comments', 'author_sort', 'title_sort', 'marked']
    def predicate(column):
        if column.is_custom and not (column.is_composite or column._is_series_index):
            return True
        else:
            return False
    
    return standard + sorted(get_columns_where(predicate).keys())

def get_possible_idents():
    """
    Get the identifiers in the library
    
    return: list(str)
    """
    return current_db().get_all_identifier_types()


def is_enum_value(name, value):
    """
    Test if the value is valide in the column enumeration
    
    name:
        Column name to test
    
    value:
        Value to test
    
    return: True / raise Error
    """
    value
    col_metadata = get_column_from_name(name)
    if not col_metadata._is_enumeration:
        raise ValueError('The column "{:s}" is not a enumeration'.format(name))
    col_vals = col_metadata.enum_values
    if not value in col_vals:
        raise ValueError('\'{:s}\' is not a valide value on the enumeration "{:s}".'.format(value, name))
    else:
        return True

def is_bool_value(value):
    """
    Test if the value is considered as a boulean by Calibre
    
    value:
        Value to test
    
    return: True / False / raise Error
    """
    if unicode(value).lower() in ['yes','y','true','1']:
        return True
    elif unicode(value).lower() in ['no','n','false','0']:
        return False
    else:
        raise ValueError('\'{:s}\' is not considered as a boulean by Calibre'.format(value))

class ColumnTypes:
    bool           = 'bool'
    datetime       = 'datetime'
    enumeration    = 'enumeration'
    identifiers    = 'identifiers'
    float          = 'float'
    integer        = 'integer'
    names          = 'names'
    rating         = 'rating'
    series         = 'series'
    series_index   = 'series_index'
    tags           = 'tags'
    text           = 'text'
    html           = 'html'
    long_text      = 'long_text'
    markdown       = 'markdown'
    title          = 'title'
    composite_tag  = 'composite_tag'
    composite_text = 'composite_text'
    
    cover          = 'cover'
    news           = 'news'

class ColumnMetadata():
    """
    You should only need the following @property of the ColumnMetadata:
    
    @property string (read-only) to identify the ColumnMetadata instance
        name
        display_name
        description
        type
        is_custom
        is_composite
    
    @property (read-only) of ColumnMetadata instance
    return is None if the column does not support this element
        allow_half_stars = bool
        category_sort = string > one of then [None, 'value', 'name'] 
        colnum = int
        column = string > one of then [None, 'value', 'name'] 
        composite_contains_html = bool
        composite_make_category = bool
        composite_sort = string > one of then ['text', 'number', 'date', 'bool']
        composite_template = string
        datatype = string
        display = {} // contains an arbitrary data set. reanalys in other property
        enum_colors = string[]
        enum_values = string[]
        heading_position = string > one of then ['text', 'number', 'date', 'bool']
        is_category = bool
        is_csp = bool
        is_editable = bool
        is_multiple = {} // contains an arbitrary data set. reanalys in other property
        kind = > one of then ['field', 'category', 'user', 'search']
        label = string
        link_column = string
        rec_index = int
        search_terms = string[]
        table = string
        use_decorations = bool
    
    @property bool (read-only) of ColumnMetadata instance
    that which identifies the type of the ColumnMetadata
        
        _is_bool
        _is_composite_tag
        _is_composite_text
        _is_datetime
        _is_enumeration
        _is_float
        _is_integer
        _is_identifiers
        _is_names
        _is_rating
        _is_series
        _is_tags
        _is_text
        _is_html
        _is_long_text
        _is_markdown
        _is_title
        
        _is_comments
        _is_news
    """
    
    def __init__(self, metadata, is_custom=True):
        self.metadata = copy.deepcopy(metadata)
        self._custom = is_custom
        
        self._multiple = self.metadata['is_multiple']
        if self.is_csp:
            self._multiple = MutipleValue({'ui_to_list': ',', 'list_to_ui': ', ', 'cache_to_list': ','})
        if self._multiple:
            self._multiple = MutipleValue(self._multiple)
        else:
            self._multiple = None
        
        self._type = None
        for func in typeproperty_registry:
            if func.__call__(self):
                self._type = regex.simple(r'^_is_', '', func.__name__)
        
        if not self._type:
            prints(self.name)
            prints('metadata',self.metadata)
            raise TypeError('Invalide Column metadata.')
    
    def __repr__(self):
        #<calibre_plugins. __module__ .common_utils.ColumnMetadata instance at 0x1148C4B8>
        #''.join(['<', str(self.__class__), ' instance at ', hex(id(self)),'>'])
        return ''.join(['<',self.name.__repr__(),' {type=', self.type,'}>'])
    
    """
        name: the key to the dictionary is:
        - for standard fields, the metadata field name.
        - for custom fields, the metadata field name prefixed by '#'
        This is done to create two 'namespaces' so the names don't clash
        
        label: the actual column label. No prefixing.
        
        datatype: the type of information in the field. Valid values are listed in
        VALID_DATA_TYPES below.
        is_multiple: valid for the text datatype. If {}, the field is to be
        treated as a single term. If not None, it contains a dict of the form
                {'cache_to_list': ',',
                'ui_to_list': ',',
                'list_to_ui': ', '}
        where the cache_to_list contains the character used to split the value in
        the meta2 table, ui_to_list contains the character used to create a list
        from a value shown in the ui (each resulting value must be strip()ed and
        empty values removed), and list_to_ui contains the string used in join()
        to create a displayable string from the list.
        
        kind == field: is a db field.
        kind == category: standard tag category that isn't a field. see news.
        kind == user: user-defined tag category.
        kind == search: saved-searches category.
        
        is_category: is a tag browser category. If true, then:
        table: name of the db table used to construct item list
        column: name of the column in the normalized table to join on
        link_column: name of the column in the connection table to join on. This
                        key should not be present if there is no link table
        category_sort: the field in the normalized table to sort on. This
                        key must be present if is_category is True
        If these are None, then the category constructor must know how
        to build the item list (e.g., formats, news).
        The order below is the order that the categories will
        appear in the tags pane.
        
        display_name: the text that is to be used when displaying the field. Column headings
        in the GUI, etc.
        
        search_terms: the terms that can be used to identify the field when
        searching. They can be thought of as aliases for metadata keys, but are only
        valid when passed to search().
        
        is_custom: the field has been added by the user.
        
        rec_index: the index of the field in the db metadata record.
        
        is_csp: field contains colon-separated pairs. Must also be text, is_multiple
        
        """
    
    
    # type property
    @property
    def name(self):
        if self._custom:
            return '#' + self.label
        else:
            if self.label == 'sort': return 'title_sort'
            return self.label
    @property
    def display_name(self):
        return self.metadata.get('name', None)
    @property
    def description(self):
        return self.display.get('description', None)
    @property
    def type(self):
        return self._type
    
    @typeproperty
    def _is_names(self):
        return bool(self.label == 'authors' or self.datatype == 'text' and self.is_multiple and self.display.get('is_names', False))
    @typeproperty
    def _is_tags(self):
        return bool(self.label == 'tags' or self.datatype == 'text' and self.is_multiple and not (self.label == 'authors' or self.display.get('is_names', False) or self.is_csp))
    
    @typeproperty
    def _is_title(self):
        return bool(self.label == 'title' or self.datatype == 'comments' and self.display.get('interpret_as', None) == 'short-text')
    
    @typeproperty
    def _is_text(self):
        return bool(self.label not in ['comments', 'title'] and self.datatype == 'text' and not self.is_multiple)
    
    @typeproperty
    def _is_series(self):
        return bool(self.datatype == 'series')
    @typeproperty
    def _is_float(self):
        return bool(self.label == 'size' or self.datatype == 'float' and self._src_is_custom and self.label != 'series_index')
    @typeproperty
    def _is_series_index(self):
        return bool(self.label == 'series_index' or self.datatype == 'float' and not self._src_is_custom and self.label != 'size')
    
    @typeproperty
    def _is_integer(self):
        return bool(self.datatype == 'int' and self.label != 'cover')
    @typeproperty
    def _is_cover(self):
        return bool(self.label == 'cover')
    @typeproperty
    def _is_datetime(self):
        return bool(self.datatype == 'datetime')
    @typeproperty
    def _is_rating(self):
        return bool(self.datatype == 'rating')
    @typeproperty
    def _is_bool(self):
        return bool(self.datatype == 'bool')
    @typeproperty
    def _is_enumeration(self):
        return bool(self.datatype == 'enumeration')
    
    @property
    def enum_values(self):
        if self._is_enumeration:
            rslt = self.display.get('enum_values', None)
            rslt.append('')
            return rslt
        else:
            return None
    @property
    def enum_colors(self):
        if self._is_enumeration:
            return self.display.get('enum_colors', None)
        else:
            return None
    
    @property
    def _is_comments(self):
        return bool(self.label == 'comments' or self.datatype == 'comments' and self.display.get('interpret_as', None) != 'short-text')
    @typeproperty
    def _is_html(self):
        return bool(self.label == 'comments' or self._is_comments and self.display.get('interpret_as', None) == 'html')
    @typeproperty
    def _is_markdown(self):
        return bool(self._is_comments and self.display.get('interpret_as', None) == 'markdown')
    @typeproperty
    def _is_long_text(self):
        return bool(self._is_comments and self.display.get('interpret_as', None)== 'long-text')
    
    @property
    def is_composite(self):
        return bool(self.datatype == 'composite')
    @typeproperty
    def _is_composite_text(self):
        return bool(self.is_composite and self.is_multiple)
    @typeproperty
    def _is_composite_tag(self):
        return bool(self.is_composite and not self.is_multiple)
    
    @typeproperty
    def _is_identifiers(self):
        return bool(self.is_csp)
    @typeproperty
    def _is_news(self):
        return bool(self.label == 'news')
    #
    
    # others
    @property
    def heading_position(self):
        # 'hide', 'above', 'side'
        if self._is_comments:
            return self.display.get('heading_position', None)
        else:
            return None
    
    @property
    def use_decorations(self):
        # 'hide', 'above', 'side'
        if self._is_text or self._is_enumeration or self._is_composite_text:
            return self.display.get('use_decorations', None)
        else:
            return None
    @property
    def allow_half_stars(self):
        if self._is_rating:
            return self.display.get('allow_half_stars', None)
        else:
            return None
    
    @property
    def composite_sort(self):
        if self.is_composite:
            return self.display.get('composite_sort', None)
        else:
            return None
    @property
    def composite_make_category(self):
        if self.is_composite:
            return self.display.get('make_category', None)
        else:
            return None
    @property
    def composite_contains_html(self):
        if self.is_composite:
            return self.display.get('contains_html', None)
        else:
            return None
    @property
    def composite_template(self):
        if self.is_composite:
            return self.display.get('composite_template', None)
        else:
            return None
    @property
    def number_format(self):
        if self._is_float:
            return self.display.get('number_format', None)
        else:
            return None
    
    @property
    def table(self):
        return self.metadata.get('table', None)
    @property
    def column(self):
        return self.metadata.get('column', None)
    @property
    def datatype(self):
        return self.metadata.get('datatype', None)
    @property
    def kind(self):
        return self.metadata.get('kind', None)
    @property
    def search_terms(self):
        return self.metadata.get('search_terms', None)
    @property
    def label(self):
        return self.metadata.get('label', None)
    @property
    def colnum(self):
        return self.metadata.get('colnum', None)
    @property
    def display(self):
        return self.metadata.get('display', None)
    @property
    def is_custom(self):
        return self._custom
    @property
    def _src_is_custom(self):
        return self.metadata.get('is_custom', None)
                    #the custom series index are not marked as custom
                    #a internal bool is nesecary
    
    @property
    def is_category(self):
        return self.metadata.get('is_category', None)
    @property
    def is_multiple(self):
        return self._multiple != None
    @property
    def multiple(self):
        return self._multiple
    @property
    def link_column(self):
        return self.metadata.get('link_column', None)
    @property
    def category_sort(self):
        return self.metadata.get('category_sort', None)
    @property
    def rec_index(self):
        return self.metadata.get('rec_index', None)
    @property
    def is_editable(self):
        return self.metadata.get('is_editable', None)
    @property
    def is_csp(self):
        """Colon-Separated Pairs, field 'identifiers'"""
        return self.metadata.get('is_csp', None)


class MutipleValue():
    def __init__(self, data):
        self._data = data
    
    def __repr__(self):
        return self._data
    
    @property
    def ui_to_list(self):
        return self._data.get('ui_to_list', None)
    @property
    def list_to_ui(self):
        return self._data.get('list_to_ui', None)
    @property
    def cache_to_list(self):
        return self._data.get('cache_to_list', None)