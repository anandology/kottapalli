#! /usr/bin/env python
"""
Sample run.py
"""
import infogami

try:
    import settings
except ImportError:
    print 'no settings found'

## your db parameters
infogami.config.db_parameters = dict(dbn='postgres', db="kottapalli2", user='anand', pw='')

## site name 
infogami.config.site = 'kottapalli.in'
infogami.config.admin_password = "admin123"

## add additional plugins and plugin path
infogami.config.plugin_path += ['plugins']
infogami.config.plugins += ['kottapalli']

def createsite():
    import web
    from infogami.infobase.infobase import Infobase
    web.config.db_parameters = infogami.config.db_parameters
    web.config.db_printing = True
    web.load()
    Infobase().create_site(infogami.config.site, infogami.config.admin_password)

if __name__ == "__main__":
    import sys
    if '--createsite' in sys.argv:
        createsite()
    else:
        infogami.run()
