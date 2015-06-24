#!/usr/bin/env python2

import os
import sys
import urllib
import base64

i = "gridsync://cmrh3t4vselhwcrdzt56rgxlcw5s2zaz@162.243.228.43:46210/DIR2:ud4yxj5zmyyxr2ue23u3kuzjwu:qc6inqijwur7xmhmovh7iovwmwykok6ibtefkpbhbe2inktytnma?n=test"
i2 = "gridsync:cmrh3t4vselhwcrdzt56rgxlcw5s2zaz@162.243.228.43:46210/DIR2:ud4yxj5zmyyxr2ue23u3kuzjwu:qc6inqijwur7xmhmovh7iovwmwykok6ibtefkpbhbe2inktytnma?n=test"
i3 = "gridsync:cmrh3t4vselhwcrdzt56rgxlcw5s2zaz@162.243.228.43:46210"

def remove_prefix(uri):
    if uri.startswith("gridsync://"):
        return uri[11:]
    elif uri.startswith("gridsync:"):
        return uri[9:]
    else:
        return uri

def uri_to_settings(uri):
    settings = { 'client': {} }
    uri = remove_prefix(uri)
    
    if '@' in uri.split('/')[0]:
        introducer = "pb://{}/introducer".format(uri.split('/')[0])
        settings['client'] = { 'introducer.furl': introducer }
        #if len(content.split('/')) > 1:


    return settings
     

print uri_to_settings(i)
print uri_to_settings(i2)
print uri_to_settings(i3)
sys.exit()

