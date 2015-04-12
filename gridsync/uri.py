#!/usr/bin/env python2

import os
import base64

from allmydata.util import base32
from pycryptopp.cipher import aes

i = "gridsync://cmrh3t4vselhwcrdzt56rgxlcw5s2zaz@162.243.228.43:46210/DIR2:ud4yxj5zmyyxr2ue23u3kuzjwu:qc6inqijwur7xmhmovh7iovwmwykok6ibtefkpbhbe2inktytnma?n=test"

def uri_to_settings(uri):
    pass

def settings_to_uri(settings):
    pass

def encrypt_link(data, key):
    pass

def decrypt_link(link, key):
    pass


def decode(string, passphrase=None):
    pass

def encode(introducer_furl, cap=None, name=None):
    pass


#cryptor = aes.AES(key='test')


def encode_link(introducer_furl, cap=None, name=None):
    s = introducer_furl.split('pb://')[1].split(',')[0]
    if root_cap:
        s = '|'.join([s, cap.split('URI:')[1]])
    if name:
        s = '|'.join([s, name])
    #print(s)
    #return "gridsync:" +base32.b2a(s).upper()
    #return "gridsync:" +base64.b32encode(s).upper()
    return s

def decode_link(link, passphrase=None):
    if link.startswith("gridsync:"):
        link = link.split("gridsync:")[1]
    #else:
    try:
        s = base32.a2b(link.lower())
        print s
        print 'hi'
    except:
        pass
    
    try:
        w = s.split('|')
        try:
            introducer_furl = "pb://{}/introducer".format(w[0])
            #print(introducer_furl)
        except:
            pass
        try:
            root_cap = "URI:{}".format(w[1])
            #print(root_cap)
        except:
            pass
        try:
            name = ' '.join(w[2:])
            #print(name)
        except:
            pass
        return introducer_furl, root_cap, name
    except:
        pass

#t = 'gridsync:Z2piNm5ob2l4YjQ2cmRxa2J3b25veXJnYWR4eHZ4NW9AMTYyLjI0My4yMjguNDM6NTIwNzQsMTI3LjAuMC4xOjUyMDc0fERJUjI6YnIzcmRlZDVjdG53cW9wbzVxejN6b3Z5cWE6eXNtYmVxeGd0Y2NsY2tvdWxwa29ucXRnNmQ3N2x1ZGk1YW55dzJ2cTdiaG40a2N2ZnFnYXxUZXN0IG5hbWU='
#bleh = 'gridsync:Z2piNm5ob2l4YjQ2cmRxa2J3b25veXJnYWR4eHZ4NW9AMTYyLjI0My4yMjguNDM6NTIwNzQsMTI3LjAuMC4xOjUyMDc0fERJUjI6YnIzcmRlZDVjdG53cW9wbzVxejN6b3Z5cWE6eXNtYmVxeGd0Y2NsY2tvdWxwa29ucXRnNmQ3N2x1ZGk1YW55dzJ2cTdiaG40a2N2ZnFnYXxOQU1FIHRlc3Q='


#print(encode_link('pb://gjb6nhoixb46rdqkbwonoyrgadxxvx5o@162.243.228.43:52074,127.0.0.1:52074/introducer', 'URI:the_uri', 'the_name'))
a = encode_link('pb://gjb6nhoixb46rdqkbwonoyrgadxxvx5o@162.243.228.43:52074,127.0.0.1:52074/introducer', 'URI:DIR2:br3rded5ctnwqopo5qz3zovyqa:ysmbeqxgtcclckoulpkonqtg6d77ludi5anyw2vq7bhn4kcvfqga', 'NAME test')
print(a)

print('--')
print(decode_link(a))

#print(decode_link(bleh))

#print(decode_link(t))
