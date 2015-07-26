# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import ConfigParser
import json
import threading
import logging
import time
import urllib2
import re

from watcher import Watcher


default_settings = {
    "node": {
        "web.port": "tcp:0:interface=127.0.0.1"
    },
    "client": {
        "shares.happy": "1",
        "shares.total": "1",
        "shares.needed": "1"
    },
    "sync": {}
}

environment = {
    "PATH": os.environ['PATH'],
    "PYTHONUNBUFFERED": '1'
}

def bin_tahoe():
    #if sys.executable.endswith('/Gridsync.app/Contents/MacOS/gridsync'):
    #    return os.path.dirname(sys.executable) + '/Tahoe-LAFS/bin/tahoe'
    for path in os.environ["PATH"].split(os.pathsep):
        tahoe_path = os.path.join(path, 'tahoe')
        if os.path.isfile(tahoe_path) and os.access(tahoe_path, os.X_OK):
            return tahoe_path


class Tahoe():
    def __init__(self, parent, tahoe_path, settings=None):
        self.parent = parent
        self.tahoe_path = os.path.expanduser(tahoe_path)
        self.settings = settings
        self.watchers = []
        self.name = os.path.basename(self.tahoe_path)
        self.use_tor = False
        self.bin_tahoe = bin_tahoe()
        if not os.path.isdir(self.tahoe_path):
            self.create()
        if self.settings:
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
        with open(os.path.join(self.tahoe_path, 'tahoe.cfg'), 'wb') as f:
            config.write(f)
    
    def setup(self, settings):
        for section, d in settings.iteritems():
            for option, value in d.iteritems():
                if section == 'tor':
                    self.use_tor = True
                    self.set_config('node', 'tub.location', 'onion.tor:1')
                elif section == 'sync':
                    self.add_watcher(option, value)
                elif section != 'sync':
                    self.set_config(section, option, value)
   
    def add_new_sync_folder(self, local_dir):
        logging.info("Adding new sync folder: %s" % local_dir)
        dircap = self.mkdir().strip()
        self.parent.settings[self.name]['sync'][local_dir] = dircap
        self.add_watcher(local_dir, dircap)
        self.restart_watchers()

    def add_watcher(self, local_dir, dircap):
        logging.info("Adding watcher: %s <-> %s" % (local_dir, dircap))
        w = Watcher(self.parent, self, local_dir, dircap)
        self.watchers.append(w)

    def start_watchers(self):
        logging.info("Starting watchers...")
        threads = [threading.Thread(target=o.start) for o in self.watchers]
        [t.start() for t in threads]

    def stop_watchers(self):
        logging.info("Stopping watchers...")
        threads = [threading.Thread(target=o.stop) for o in self.watchers]
        [t.start() for t in threads]
        [t.join() for t in threads]

    def restart_watchers(self):
        logging.info("Restarting watchers...")
        self.stop_watchers()
        self.start_watchers()

    def node_url(self):
        with open(os.path.join(self.tahoe_path, 'node.url')) as f:
            return f.read().strip()

    def connection_status(self):
        # https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2476
        html = urllib2.urlopen(self.node_url()).read()
        p = re.compile("Connected to <span>(.+?)</span>")
        servers_connected = int(re.findall(p, html)[0])
        p = re.compile("of <span>(.+?)</span> known storage servers")
        servers_known = int(re.findall(p, html)[0])
        return servers_connected, servers_known

    def command(self, args):
        args = ['tahoe', '-d', self.tahoe_path] + args
        if self.use_tor:
            args.insert(0, 'torsocks')
        logging.debug("Running: %s" % ' '.join(args))
        proc = subprocess.Popen(args, env=environment, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, universal_newlines=True)
        output = ''
        for line in iter(proc.stdout.readline, ''):
            logging.debug("[pid:%d] %s" % (proc.pid, line.rstrip()))
            self.parent.status_text = line.strip() # XXX Make this more useful
        proc.poll()
        if proc.returncode is None:
            logging.error("[pid:%d] No return code for %s" % (proc.pid, args))
        else:
            logging.debug("[pid:%d] %d" % (proc.pid, proc.returncode))

    def command_output(self, args):
        if isinstance(args, list):
            args = ['tahoe', '-d', self.tahoe_path] + args
        else:
            args = ['tahoe', '-d', self.tahoe_path] + args.split()
        if self.use_tor:
            args.insert(0, 'torsocks')
        logging.debug("Running: %s" % ' '.join(args))
        out = subprocess.check_output(args, stderr=subprocess.STDOUT,
                universal_newlines=True)
        return out

    def create(self):
        self.command(['create-client'])
    
    def start(self):
        if not os.path.isfile(os.path.join(self.tahoe_path, 'twistd.pid')):
            self.command(['start'])
        else:
            pid = int(open(os.path.join(self.tahoe_path, 'twistd.pid')).read())
            try:
                os.kill(pid, 0)
            except OSError:
                self.command(['start'])
        time.sleep(3) # XXX Fix; watch for command output instead of waiting.
        self.start_watchers()

    def stop(self):
        self.command(['stop'])
    
    def mkdir(self):
        return self.command_output('mkdir').strip()

    def backup(self, local_dir, remote_dircap):
        self.command(["backup", "-v", "--exclude=*.gridsync-versions*", 
                local_dir, remote_dircap])

    def get(self, remote_uri, local_file, mtime=None):
        self.command(["get", remote_uri, local_file]) 
        if mtime:
            os.utime(local_file, (-1, mtime))

    def get_metadata(self, dircap, basedir='/', metadata={}):
        # XXX Fix this...
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
                            target=self.get_metadata, args=(
                                dircap, path, metadata)))
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
        [t.start() for t in threads]
        [t.join() for t in threads]
        return metadata
