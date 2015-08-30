# -*- coding: utf-8 -*-

import ConfigParser
import json
import logging
import os
import re
import subprocess
import urllib2


DEFAULT_SETTINGS = {
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

ENVIRONMENT = {
    "PATH": os.environ['PATH'],
    "PYTHONUNBUFFERED": '1'
}


class Tahoe():
    def __init__(self, node_dir=None, settings=None):
        if not node_dir:
            self.node_dir = os.path.join(os.path.expanduser('~'), '.tahoe')
        else:
            self.node_dir = os.path.expanduser(node_dir)
        self.settings = settings
        self.name = os.path.basename(self.node_dir)
        self.use_tor = False
        self.connection_status = {}
        if not os.path.isdir(self.node_dir):
            self.create()
        if self.settings:
            self.setup(settings)

    def get_config(self, section, option):
        config = ConfigParser.RawConfigParser(allow_no_value=True)
        config.read(os.path.join(self.node_dir, 'tahoe.cfg'))
        return config.get(section, option)

    def set_config(self, section, option, value):
        logging.debug("Setting {} option {} to: {}".format(section, option, value))
        config = ConfigParser.RawConfigParser(allow_no_value=True)
        config.read(os.path.join(self.node_dir, 'tahoe.cfg'))
        config.set(section, option, value)
        with open(os.path.join(self.node_dir, 'tahoe.cfg'), 'wb') as f:
            config.write(f)

    def setup(self, settings):
        for section, d in settings.iteritems():
            for option, value in d.iteritems():
                # To be changed when Tahoe-LAFS ticket #517 closes
                # https://tahoe-lafs.org/trac/tahoe-lafs/ticket/517
                if section == 'tor':
                    self.use_tor = True
                    self.set_config('node', 'tub.location', 'onion.tor:1')
                elif section == 'sync':
                    #self.add_sync_folder(option, value)
                    pass
                else:
                    self.set_config(section, option, value)

    def node_url(self):
        with open(os.path.join(self.node_dir, 'node.url')) as f:
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
                self.connection_status['servers'][nodeid[index - 2]]['status'] = status

    def command(self, args):
        args = ['tahoe', '-d', self.node_dir] + args
        if self.use_tor:
            args.insert(0, 'torsocks')
        logging.debug("Running: {}".format(' '.join(args)))
        proc = subprocess.Popen(args, env=ENVIRONMENT, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, universal_newlines=True)
        output = ''
        for line in iter(proc.stdout.readline, ''):
            logging.debug("[pid:{}] {}".format(proc.pid, line.rstrip()))
            output = output + line
        proc.poll()
        if proc.returncode is None:
            logging.warning("No return code for pid:{} ({})".format(
                    proc.pid, ' '.join(args)))
        else:
            logging.debug("pid:{} ({}) returned {}".format(
                    proc.pid, ' '.join(args), proc.returncode))
            return output.rstrip()

    def ls_json(self, dircap):
        args = ['tahoe', '-d', self.node_dir, 'ls', '--json', dircap]
        output = subprocess.check_output(args, universal_newlines=True)
        return json.loads(output)

    def create(self):
        self.command(['create-client'])

    def start(self):
        if not os.path.isfile(os.path.join(self.node_dir, 'twistd.pid')):
            self.command(['start'])
        else:
            pid = int(open(os.path.join(self.node_dir, 'twistd.pid')).read())
            try:
                os.kill(pid, 0)
            except OSError:
                self.command(['start'])

    def stop(self):
        self.command(['stop'])

    def mkdir(self):
        dircap = self.command(['mkdir'])
        logging.debug("Created dircap: {}".format(dircap))
        return dircap

    def backup(self, local_dir, remote_dircap):
        output = self.command(["backup", "-v",
            "--exclude=*.gridsync-versions*", local_dir, remote_dircap])
        return output

    def get(self, remote_uri, local_filepath):
        self.command(["get", remote_uri, local_filepath])

