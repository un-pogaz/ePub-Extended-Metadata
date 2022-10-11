#!/usr/bin/python

__license__   = 'GPL v3'
__copyright__ = '2022, un_pogaz based on code from JimmXinu and Grant Drake'

'''
Creates an uncompressed zip file for the plugin.
Plugin zips are uncompressed so to not negatively impact calibre load times.

1. Derive the plugin zip filename by reading __init__.py in plugin folder
2. Also derive the version (for printing)

All subfolders of the plugin folder will be included, unless prefixed with '.'
i.e. .build and .tx will not be included in the zip.
'''

import os, zipfile, re, shutil
from glob import glob

CALIBRE_CONFIG_DIRECTORY = os.environ.get('CALIBRE_CONFIG_DIRECTORY', os.path.join(os.environ.get('appdata'), 'calibre'))
PLUGINS_DIRECTORY = os.path.join(CALIBRE_CONFIG_DIRECTORY, 'plugins')

def get_calibre_bin(calibre_bin):
    return os.path.join(os.environ.get('CALIBRE_DIRECTORY', ''), calibre_bin)

def run_command(command_line, wait=False):
    """
    Lauch a command line and return the subprocess
    
    :type filepath:     string
    :param filepath:    Path to the file to open
    :type wait:         bool
    :param wait:        Wait for the file to be closed
    :rtype:             subprocess
    :return:            The pointer the subprocess returned by the Popen call
    """
    
    import os
    from subprocess import Popen, PIPE
    
    if not isinstance(command_line, str):
        for idx in range(len(command_line)):
            if ' ' in command_line[idx]: command_line[idx] = '"'+command_line[idx]+'"'
        command_line = ' '.join(command_line)
    
    subproc = Popen(command_line, stdout=PIPE, stderr=PIPE, shell=True)
    if wait:
        subproc.wait()
    return subproc

def read_plugin_name():
    init_file = os.path.join(os.getcwd(), '__init__.py')
    if not os.path.exists(init_file):
        print('ERROR: No __init__.py file found for this plugin')
        raise FileNotFoundError(init_file)
    
    zip_file_name = None
    with open(init_file, 'r') as file:
        content = file.read()
        nameMatches = re.findall("\s+name\s*=\s*\'([^\']*)\'", content)
        if nameMatches: 
            zip_file_name = nameMatches[0]+'.zip'
        else:
            raise RuntimeError('Could not find plugin name in __init__.py')
        version_matches = re.findall("\s+version\s*=\s*\(([^\)]*)\)", content)
        if version_matches: 
            version = version_matches[0].replace(',','.').replace(' ','')
    
    print("Plugin v{} will be zipped to: '{}'".format(version, zip_file_name))
    return zip_file_name, version

def update_translations():
    for po in glob('translations/**/*.po', recursive=True):
        run_command([get_calibre_bin('calibre-debug'), '-c', 'from calibre.translations.msgfmt import main; main()', os.path.abspath(po)], wait=True)

def create_zip_file(filename, mode, files):
    with zipfile.ZipFile(filename, mode, zipfile.ZIP_STORED) as zip:
        for file in files:
            if os.path.isfile(file):
                zip.write(file, file)

def build_plugin():
    
    PLUGIN, version = read_plugin_name()
    
    update_translations()
    
    files = []
    files.extend(glob('plugin-import-name-*.txt'))
    files.extend(glob('**/*.py', recursive=True))
    files.extend(glob('images/**/*.png', recursive=True))
    files.extend(glob('translations/*.pot'))
    files.extend(glob('translations/*.mo'))
    files.extend(glob('translations/*.po'))
    files.extend(glob('**/*.md', recursive=True))
    files.extend(glob('**/*.html', recursive=True))
    files.extend(glob('**/*.cmd', recursive=True))
    files.extend(glob('LICENSE'))
    files.extend(glob('CREDITS'))
    
    create_zip_file(PLUGIN, 'w', files)
    
    run_command([get_calibre_bin('calibre-customize'), '-a', PLUGIN], wait=True)
    
    versioning = os.path.join(os.getcwd(), '-- versioning')
    if os.path.exists(versioning) and os.path.isdir(versioning):
        out = os.path.join(versioning, PLUGIN)
        if os.path.exists(out): os.remove(out)
        os.rename(PLUGIN, out)
    else:
        os.remove(PLUGIN)
    
    print("Plugin '{}' build with succes.".format(PLUGIN))

if __name__=="__main__":
    build_plugin()