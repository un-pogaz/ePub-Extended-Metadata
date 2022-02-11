#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2021, un_pogaz <un.pogaz@gmail.com>'
__docformat__ = 'restructuredtext en'

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

FILES_TYPES             = {'epub'}
class NAME:
    BASE                = 'ePub Extended Metadata'
    READER              = BASE + ' {Reader}'
    WRITER              = BASE + ' {Writer}'
class DESCRIPTION:
    ACTION              = _('Read and write a wider range of metadata for ePub\'s files and associating them to columns in your libraries.')
    COMPANION           = '\n' +_('This is an companion (and auto instaled) plugin of "{:s}".').format(NAME.BASE)
    READER              = _('Read a wider range of metadata from the ePub file.') + COMPANION
    WRITER              = _('Write a wider range of metadata in the ePub file.') + COMPANION
SUPPORTED_PLATFORMS     = ['windows', 'osx', 'linux']
AUTHOR                  = 'un_pogaz'
VERSION                 = (0, 6, 0)
MINIMUM_CALIBRE_VERSION = (4, 0, 0)