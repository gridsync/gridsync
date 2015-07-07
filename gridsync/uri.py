# -*- coding: utf-8 -*-

import os
import sys
import urllib
import base64


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
     
def decode_uri(uri):
    if len(uri) % 8 != 0:
        while len(uri) % 8 != 0:
            uri = uri + "="
        return base64.b32decode(uri)
    else:
        return base64.b32decode(uri)

def encode_uri(uri):
    return base64.b32encode(uri).replace('=', '')
