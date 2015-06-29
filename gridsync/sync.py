# -*- coding: utf-8 -*-

import os
import shutil
import datetime
import threading
import logging


def _get_local_mtimes(basedir):
    local_mtimes = {}
    for root, dirs, files in os.walk(basedir, followlinks=True):
        for name in files:
            fn = os.path.join(root, name)
            local_mtimes[fn] = os.path.getmtime(fn)
        for name in dirs:
            fn = os.path.join(root, name)
            local_mtimes[fn] = os.path.getmtime(fn)
    return local_mtimes

def _create_conflicted_copy(file, mtime):
    base, extension = os.path.splitext(file)
    t = datetime.datetime.fromtimestamp(mtime)
    tag = t.strftime('.(conflicted copy %Y-%m-%d %H-%M-%S)')
    newname = base + tag + extension
    shutil.copy2(file, newname)

def sync(tahoe, local_dir, remote_dircap, snapshot='Latest'):
    logging.info("*** Syncing {}...".format(local_dir))
    local_dir = os.path.expanduser(local_dir)
    remote_dircap = '/'.join([remote_dircap, snapshot])
    local_mtimes = _get_local_mtimes(local_dir) # store this in Watcher()?
    remote_mtimes = tahoe.get_metadata(remote_dircap, metadata={})
    do_backup = False
    threads = []
    for file, metadata in remote_mtimes.items():
        if metadata['type'] == 'dirnode':
            dir = os.path.join(local_dir, file)
            if not os.path.isdir(dir):
                os.makedirs(dir)
    for file, metadata in remote_mtimes.items():
        if metadata['type'] == 'filenode':
            file = os.path.join(local_dir, file)
            if file in local_mtimes:
                local_mtime = int(local_mtimes[file])
                remote_mtime = int(metadata['mtime']) # :/
                if remote_mtime > local_mtime:
                    logging.debug("[@] %s older than stored version, scheduling download" % file)
                    _create_conflicted_copy(file, local_mtime)
                    threads.append(
                            threading.Thread(
                                target=tahoe.get, 
                                args=(metadata['uri'], file, remote_mtime)))
                elif remote_mtime < local_mtime:
                    logging.debug("[*] %s is newer than stored version, scheduling backup" % file)
                    do_backup = True
                else:
                    logging.debug("[v] %s is up to date." % file)
            else:
                logging.debug("[?] %s is missing, scheduling download" % file)
                threads.append(
                        threading.Thread(
                            target=tahoe.get, 
                            args=(metadata['uri'], file, metadata['mtime'])))
    for file, metadata in local_mtimes.items():
        if file.split(local_dir + os.path.sep)[1] not in remote_mtimes:
            logging.debug("[!] %s isn't stored, scheduling backup" % file)
            do_backup = True
    [t.start() for t in threads]
    [t.join() for t in threads]
    if do_backup:
        tahoe.backup(local_dir, remote_dircap)

