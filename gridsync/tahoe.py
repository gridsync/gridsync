# -*- coding: utf-8 -*-

import os
import subprocess
import ConfigParser
import json
import threading
import logging


class Tahoe():
    def __init__(self, tahoe_path, settings=None):
        self.tahoe_path = os.path.expanduser(tahoe_path)
        if not os.path.isdir(self.tahoe_path):
            self.create()
        if settings:
            self.setup(settings)

    def get_config(self, section, option):
        config = ConfigParser.RawConfigParser(allow_no_value=True)
        config.read(os.path.join(self.tahoe_path, 'tahoe.cfg'))
        return config.get(section, option)
    
    def set_config(self, section, option, value):
        logging.debug("Setting %s option %s to: %s" % (section, option, value))
        config = ConfigParser.RawConfigParser(allow_no_value=True)
        config.read(os.path.join(self.tahoe_path, 'tahoe.cfg'))
        config.set(section, option, value)
        with open(os.path.join(self.tahoe_path, 'tahoe.cfg'), 'wb') as config_file:
            config.write(config_file)
    
    def setup(self, settings):
        for section, d in settings.iteritems():
            for option, value in d.iteritems():
                self.set_config(section, option, value)

    def command(self, args):
        args = ['tahoe', '-d', self.tahoe_path] + args.split()
        logging.debug("Running: %s" % ' '.join(args))
        ret = subprocess.call(args, stderr=subprocess.STDOUT,
                universal_newlines=True)
        return ret
    
    def command_output(self, args):
        args = ['tahoe', '-d', self.tahoe_path] + args.split()
        logging.debug("Running: %s" % ' '.join(args))
        out = subprocess.check_output(args, stderr=subprocess.STDOUT,
                universal_newlines=True)
        return out

    def create(self):
        self.command('create-client')
    
    def start(self):
        if not os.path.isfile(os.path.join(self.tahoe_path, 'twistd.pid')):
            self.command('start')
        else:
            pid = int(open(os.path.join(self.tahoe_path, 'twistd.pid')).read())
            try:
                os.kill(pid, 0)
            except OSError:
                self.command('start')

    def stop(self):
        self.command('stop')
    
    def backup(self, local_dir, remote_dircap):
        self.command("backup -v %s %s" % (local_dir, remote_dircap))

    def get(self, remote_uri, local_file, mtime=None):
        args = ['tahoe', '-d', self.tahoe_path, 'get', remote_uri, local_file]
        ret = subprocess.call(args, stderr=subprocess.STDOUT,
                universal_newlines=True)
        if mtime:
            os.utime(local_file, (-1, mtime))
        return ret

    def get_metadata(self, dircap, basedir='/', metadata={}):
        logging.debug("Getting remote metadata...")
        out = self.command_output("ls --json %s" % dircap)
        j = json.loads(out)
        threads = []
        for k, v in j[1]['children'].items():
            if v[0] == 'dirnode':
                path = os.path.join(basedir, k).strip('/')
                if 'rw_uri' in v[1]:
                    dircap =  v[1]['rw_uri']
                else:
                    dircap =  v[1]['ro_uri']
                metadata[path] = {
                    'type': 'dirnode',
                    'format': 'DIR',
                    'uri': dircap,
                    'mtime': 0,
                    'size': 0
                }
                threads.append(
                        threading.Thread(
                            target=self.get_metadata, args=(dircap, path, metadata)))
                #self.get_metadata(dircap, path, metadata)
            elif v[0] == 'filenode':
                path = os.path.join(basedir, k).strip('/')
                for a, m in v[1]['metadata'].items():
                    if a == 'mtime':
                        mtime = m
                if 'rw_uri' in v[1]:
                    dircap =  v[1]['rw_uri']
                else:
                    dircap =  v[1]['ro_uri']
                metadata[path] = {
                    'type': 'filenode',
                    'format': v[1]['format'],
                    'mtime': mtime,
                    'uri': dircap,
                    'size': v[1]['size']
                }
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return metadata
