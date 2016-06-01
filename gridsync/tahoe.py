# -*- coding: utf-8 -*-

import hashlib
import logging
import math
import os
import re
import sqlite3
import subprocess
import sys
import time

import requests

from gridsync.config import Config
from gridsync.util import h2b, b2h

if sys.version_info.major == 2:
    import ConfigParser as configparser
else:
    import configparser


DEFAULT_SETTINGS = {
    "node": {
        "web.port": "tcp:0:interface=127.0.0.1"
    },
    "client": {
        "shares.happy": "1",
        "shares.total": "1",
        "shares.needed": "1"
    },
}


def decode_introducer_furl(furl):
    """Return (tub_id, connection_hints)"""
    p = r'^pb://([a-z2-7]+)@([a-zA-Z0-9\.:,-]+:\d+)/[a-z2-7]+$'
    m = re.match(p, furl.lower())
    return m.group(1), m.group(2)


class Tahoe():
    def __init__(self, location=None, settings=None):
        self.location = location  # introducer fURL, gateway URL, or local path
        self.settings = settings
        self.node_dir = None
        self.node_url = None
        self.status = {}
        if not location:
            pass
        elif location.startswith('pb://'):
            if not self.settings:
                self.settings = DEFAULT_SETTINGS
            self.settings['client']['introducer.furl'] = location
            _, connection_hints = decode_introducer_furl(location)
            first_hostname = connection_hints.split(',')[0].split(':')[0]
            self.node_dir = os.path.join(Config().config_dir, first_hostname)
        elif location.startswith('http://') or location.startswith('https://'):
            location += ('/' if not location.endswith('/') else '')
            self.node_url = location
        else:
            self.node_dir = os.path.join(Config().config_dir, location)
        if self.node_dir:
            self.name = os.path.basename(self.node_dir)
        else:
            self.name = location

    def get_config(self, section, option):
        config = configparser.RawConfigParser(allow_no_value=True)
        config.read(os.path.join(self.node_dir, 'tahoe.cfg'))
        return config.get(section, option)

    def set_config(self, section, option, value):
        # XXX: This should probably preserve commented ('#'-prefixed) lines..
        logging.debug("Setting {} option {} to: {}".format(
            section, option, value))
        config = configparser.RawConfigParser(allow_no_value=True)
        config.read(os.path.join(self.node_dir, 'tahoe.cfg'))
        config.set(section, option, value)
        with open(os.path.join(self.node_dir, 'tahoe.cfg'), 'w') as f:
            config.write(f)

    def setup(self, settings):
        for section, d in settings.items():
            for option, value in d.items():
                self.set_config(section, option, value)

    def command(self, args, quiet=False, num_attempts=1):
        tahoe_exe = 'tahoe' + ('.exe' if sys.platform == 'win32' else '')
        if self.node_dir:
            full_args = [tahoe_exe, '-d', self.node_dir] + args
        else:
            full_args = [tahoe_exe] + args
        env = os.environ
        env['PYTHONUNBUFFERED'] = '1'
        if not quiet:
            logging.debug("Running: {}".format(' '.join(full_args)))
        try:
            if sys.platform == 'win32':
            # https://msdn.microsoft.com/en-us/library/ms684863%28v=VS.85%29.aspx
                proc = subprocess.Popen(
                    full_args, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, universal_newlines=True,
                    creationflags=0x08000000)
            else:
                proc = subprocess.Popen(
                    full_args, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, universal_newlines=True)
        except OSError as error:
            logging.error("Could not run tahoe executable: {}".format(error))
            # TODO: Notify user?
            raise
            return
        output = ''
        for line in iter(proc.stdout.readline, ''):
            if not quiet:
                logging.debug("[pid:{}] {}".format(proc.pid, line.rstrip()))
            output = output + line
        proc.poll()
        if proc.returncode:
            logging.error("pid {} ({}) excited with code {}".format(
                proc.pid, ' '.join(full_args), proc.returncode))
            num_attempts -= 1
            if num_attempts:
                logging.debug("Trying again ({} attempts remaining)...".format(
                    num_attempts))
                time.sleep(1)
                self.command(args, quiet, num_attempts)
            else:
                raise RuntimeError(output.rstrip())
        elif proc.returncode is None:
            logging.warning("No return code for pid:{} ({})".format(
                proc.pid, ' '.join(full_args)))
        elif not quiet:
                logging.debug("pid {} ({}) excited with code {}".format(
                    proc.pid, ' '.join(full_args), proc.returncode))
        return output.rstrip()

    def start(self):
        logging.debug("Starting Tahoe-LAFS gateway: {}".format(self.location))
        if not self.node_dir:
            logging.debug("Tahoe-LAFS gateway {} is running remotely; "
                          "no need to start".format(self.node_url))
            return
        elif not os.path.isdir(self.node_dir):
            logging.debug("{} not found; "
                          "creating node dir...".format(self.node_dir))
            self.command(['create-client'])
        elif not os.path.isfile(os.path.join(self.node_dir, 'tahoe.cfg')):
            logging.debug("{} found but tahoe.cfg is missing; "
                          "(re)creating node dir...".format(self.node_dir))
            self.command(['create-client'])
        if self.settings:
            self.setup(self.settings)
        if not os.path.isfile(os.path.join(self.node_dir, 'twistd.pid')):
            self.command(['start'])
        else:
            pid = int(open(os.path.join(self.node_dir, 'twistd.pid')).read())
            try:
                os.kill(pid, 0)
            except OSError:
                self.command(['start'])
        self.node_url = open(os.path.join(self.node_dir,
                             'node.url')).read().strip()
        logging.debug("Node URL is: {}".format(self.node_url))

    def mkdir(self):
        # TODO: Allow subdirs?
        url = self.node_url + 'uri?t=mkdir'
        r = requests.post(url)
        r.raise_for_status()
        return r.content.decode()

    def ls(self, dircap):
        url = self.node_url + 'uri/' + dircap + '?t=json'
        r = requests.get(url)
        r.raise_for_status()
        items = [item for item in r.json()[1]['children'].keys()]
        return sorted(items)

    def get_info(self, cap):
        url = self.node_url + 'uri/' + cap + '?t=json'
        r = requests.get(url)
        r.raise_for_status()
        return r.json()

    def get_operations(self):
        url = self.node_url + 'status?t=json'
        r = requests.get(url)
        r.raise_for_status()
        return r.json()['active']

    def get_sharemap(self, storage_index):
        url = self.node_url + 'status/'
        html = requests.get(url).text
        lines = html.split('\n')
        for i, line in enumerate(lines):
            if storage_index in line:
                operation_url = url + lines[i + 4].split('"')[1]
                break
        try:
            html = requests.get(operation_url).text
        except:
            return
        lines = html.split('\n')
        sharemap = {}
        for line in lines:
            if "Sharemap:" in line:
                mappings = line.split('<li>')[2:]
                for mapping in mappings:
                    share = mapping.split('-&gt;')[0]
                    server = mapping.split('[')[1].split(']')[0]
                    sharemap[share] = server
                return sharemap

    def update_status(self):
        # https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2476
        html = requests.get(self.node_url).text
        p = re.compile("Connected to <span>(.+?)</span>")
        self.status['servers_connected'] = int(re.findall(p, html)[0])
        p = re.compile("of <span>(.+?)</span> known storage servers")
        self.status['servers_known'] = int(re.findall(p, html)[0])

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
        self.status['introducer'] = {'furl': r[0]}
        self.status['helper'] = {'furl': r[1]}
        self.status['servers'] = servers

        p = re.compile('<div class="status-indicator">(.+?)</div>')
        l = re.findall(p, html)
        for index, item in enumerate(l):
            p = re.compile('alt="(.+?)"')
            status = re.findall(p, item)[0]
            if index == 0:
                self.status['introducer']['status'] = status
            elif index == 1:
                self.status['helper']['status'] = status
            else:
                self.status['servers'][nodeid[index - 2]]['status'] = status
        total_available_space = 0
        for _, v in self.status['servers'].items():
            try:
                total_available_space += h2b(v['available_space'])
            except ValueError:
                pass
        self.status['total_available_space'] = b2h(total_available_space)

    def adjust(self):
        """Adjust erasure coding paramaters to Sensible(tm) values

        'Sensible' here is determined in accordance with the number of
        available storage nodes, where N = the total number of currently
        available nodes, K = (N * 0.3), and H = (N * 0.7).

        Adjusting these values is followed by restarting the running node.
        """
        logging.debug("Adjusting erasure coding parameters...")
        shares_total = int(self.status.get('servers_connected', 1))  # N
        shares_needed = int(math.ceil(shares_total * 0.3))  # K
        shares_happy = int(math.ceil(shares_total * 0.7))  # H
        self.set_config('client', 'shares.total', shares_total)
        self.set_config('client', 'shares.needed', shares_needed)
        self.set_config('client', 'shares.happy', shares_happy)
        self.command(['stop'])
        self.start()

    def stored(self, filepath, size=None, mtime=None):
        """Return filecap if filepath has been stored previously via backup"""
        if not size:
            try:
                size = os.path.getsize(filepath)
            except OSError:
                return
        if not mtime:
            try:
                mtime = int(os.path.getmtime(filepath))
            except OSError:
                return
        db = os.path.join(self.node_dir, 'private', 'backupdb.sqlite')
        if not os.path.isfile(db):
            return
        connection = sqlite3.connect(db)
        with connection:
            try:
                cursor = connection.cursor()
                cursor.execute(
                    'SELECT "filecap" FROM "caps" WHERE fileid=('
                    'SELECT "fileid" FROM "local_files" WHERE path=? '
                    'AND size=? AND mtime=?)', (filepath, size, mtime))
                return cursor.fetchone()[0]
            except:
                return

    def get_aliases(self):
        aliases = {}
        aliases_file = os.path.join(self.node_dir, 'private', 'aliases')
        try:
            with open(aliases_file) as f:
                for line in f.readlines():
                    if not line.startswith('#'):
                        try:
                            name, cap = line.split(':', 1)
                            aliases[name + ':'] = cap.strip()
                        except ValueError:
                            pass
            return aliases
        except IOError:
            return

    def get_dircap_from_alias(self, alias):
        if not alias.endswith(':'):
            alias = alias + ':'
        try:
            for name, cap in self.get_aliases().items():
                if name == alias:
                    return cap
        except AttributeError:
            return

    def get_alias_from_dircap(self, dircap):
        try:
            for name, cap in self.get_aliases().items():
                if cap == dircap:
                    return name
        except AttributeError:
            return

    def aliasify(self, dircap_or_alias):
        """Return a valid alias corresponding to a given dircap or alias.

        Return the alias of the given dircap, if it already exists, or, if
        it doesn't, add and return an alias using the SHA-256 hash of the
        dircap as the name.

        If an alias is passed instead of a dircap, return it only if it
        corresponds to a valid dircap, raising a ValueError if the dircap
        is invalid, or a LookupError if it is missing from the aliases file.
        """
        if dircap_or_alias.startswith('URI:DIR'):
            alias = self.get_alias_from_dircap(dircap_or_alias)
            if alias:
                return alias
            else:
                hash_of_dircap = hashlib.sha256(
                    dircap_or_alias.encode('utf-8')).hexdigest()
                self.command(['add-alias', hash_of_dircap, dircap_or_alias])
                return self.get_alias_from_dircap(dircap_or_alias)
        else:
            dircap = self.get_dircap_from_alias(dircap_or_alias)
            if dircap:
                if dircap.startswith('URI:DIR'):
                    return dircap_or_alias
                else:
                    raise ValueError('Invalid alias for {} ({})'.format(
                        dircap_or_alias, dircap))
            #else:
            #    self.command(['create-alias', dircap_or_alias])
            #    return dircap_or_alias
            else:
                raise LookupError('No dircap found for alias {}'.format(
                    dircap_or_alias))
