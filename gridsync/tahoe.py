# -*- coding: utf-8 -*-

import ConfigParser
import json
import logging
import os
import re
import subprocess
import threading
import time
import urllib2

from twisted.internet import reactor
from twisted.internet.task import LoopingCall

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
        self.connection_status = {}
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
        for watcher in self.watchers:
            reactor.callInThread(watcher.start)

    def stop_watchers(self):
        logging.info("Stopping watchers...")
        for watcher in self.watchers:
            reactor.callInThread(watcher.stop)

    def restart_watchers(self):
        logging.info("Restarting watchers...")
        self.stop_watchers()
        self.start_watchers()

    def node_url(self):
        with open(os.path.join(self.tahoe_path, 'node.url')) as f:
            return f.read().strip()

    def update_connection_status(self):
        # https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2476
        html = urllib2.urlopen(self.node_url()).read()
        p = re.compile("Connected to <span>(.+?)</span>")
        self.connection_status['servers_connected'] = int(re.findall(p, html)[0])
        p = re.compile("of <span>(.+?)</span> known storage servers")
        self.connection_status['servers_known'] = int(re.findall(p, html)[0])

        servers = {}
        p = re.compile('<div class="nodeid">(.+?)</div>')
        nodeid = re.findall(p, html)
        for item in nodeid:
            servers[item] = {}

        def insert_all(s, tag='td'):
            p = re.compile('<{} class="{}">(.+?)</{}>'.format(tag, s, tag))
            for index, item in enumerate(re.findall(p, html)):
                key = s.replace('service-', '').replace('-', '_').replace(' ', '_')
                servers[nodeid[index]][key] = item

        insert_all('nickname', 'div')
        insert_all('address')
        insert_all('service-service-name')
        insert_all('service-since timestamp')
        insert_all('service-announced timestamp')
        insert_all('service-version')
        insert_all('service-available-space')

        p = re.compile('<div class="furl">(.+?)</div>')
        r = re.findall(p, html)
        self.connection_status['introducer'] = { 'furl': r[0] }
        self.connection_status['helper'] = { 'furl': r[1] }
        self.connection_status['servers'] = servers

        p = re.compile('<div class="status-indicator">(.+?)</div>')
        l = re.findall(p, html)
        for index, item in enumerate(l):
            p = re.compile('alt="(.+?)"')
            status = re.findall(p, item)[0]
            if index == 0:
                self.connection_status['introducer']['status'] = status
            elif index == 1:
                self.connection_status['helper']['status'] = status
            else:
                t = self.connection_status['servers'][nodeid[index - 2]]['status'] = status

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
            output = output + line
            self.parent.status_text = line.strip() # XXX Make this more useful
        proc.poll()
        if proc.returncode is None:
            logging.error("[pid:%d] No return code for %s" % (proc.pid, args))
        else:
            logging.debug("[pid:%d] %d" % (proc.pid, proc.returncode))
            return output.rstrip()

    def ls_json(self, dircap):
        args = ['tahoe', '-d', self.tahoe_path, 'ls', '--json']
        args.append(dircap)
        output = subprocess.check_output(args, stderr=subprocess.STDOUT,
                universal_newlines=True)
        return json.loads(output)

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
        time.sleep(2)
        update_connection_status_loop = LoopingCall(self.update_connection_status)
        update_connection_status_loop.start(60)

    def stop(self):
        self.stop_watchers()
        self.command(['stop'])

    def mkdir(self):
        return self.command(['mkdir'])

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
        j = self.ls_json(dircap)
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

