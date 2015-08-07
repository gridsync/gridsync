# -*- coding: utf-8 -*-

import datetime
import logging
import os
import shutil
import threading


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

def _create_conflicted_copy(filename, mtime):
    base, extension = os.path.splitext(filename)
    t = datetime.datetime.fromtimestamp(mtime)
    tag = t.strftime('.(conflicted copy %Y-%m-%d %H-%M-%S)')
    newname = base + tag + extension
    shutil.copy2(filename, newname)

def _create_versioned_copy(local_dir, filename, mtime):
    versions_dir = os.path.join(local_dir, '.gridsync-versions')
    local_filepath = os.path.join(local_dir, filename)
    base, extension = os.path.splitext(filename)
    t = datetime.datetime.fromtimestamp(mtime)
    tag = t.strftime('.(%Y-%m-%d %H-%M-%S)')
    versioned_filepath = os.path.join(versions_dir, base + tag + extension)
    if not os.path.isdir(os.path.dirname(versioned_filepath)):
        os.makedirs(os.path.dirname(versioned_filepath))
    logging.info("Copying version of {} to {}".format(local_filepath, versioned_filepath))
    shutil.copy2(local_filepath, versioned_filepath)

def get_metadata(tahoe, dircap, basedir='/', metadata={}):
    # XXX Fix this...
    logging.debug("Getting remote metadata...")
    j = tahoe.ls_json(dircap)
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
                        target=get_metadata, args=(
                            tahoe, dircap, path, metadata)))
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

def sync(tahoe, local_dir, remote_dircap, snapshot='Latest'):
    tahoe.parent.sync_state += 1
    # XXX Here be dragons!
    # This all needs to be re-written/re-factored/re-considered...
    logging.info("*** Syncing {}...".format(local_dir))
    local_dir = os.path.expanduser(local_dir)
    remote_path = '/'.join([remote_dircap, snapshot])
    local_mtimes = _get_local_mtimes(local_dir) # store this in Watcher()?
    remote_mtimes = get_metadata(tahoe, remote_path, metadata={})
    do_backup = False
    threads = []
    for file, metadata in remote_mtimes.items():
        if metadata['type'] == 'dirnode':
            dir = os.path.join(local_dir, file)
            if not os.path.isdir(dir):
                os.makedirs(dir)
    for file, metadata in remote_mtimes.items():
        if metadata['type'] == 'filenode':
            remote_filepath = file
            file = os.path.join(local_dir, file)
            if file in local_mtimes:
                local_mtime = int(local_mtimes[file])
                remote_mtime = int(metadata['mtime']) # :/
                if remote_mtime > local_mtime:
                    logging.debug("[@] {} older than stored version, scheduling download".format(file))
                    #_create_conflicted_copy(file, local_mtime)
                    _create_versioned_copy(local_dir, remote_filepath, local_mtime)
                    threads.append(
                            threading.Thread(
                                target=tahoe.get, 
                                args=(metadata['uri'], file, remote_mtime)))
                elif remote_mtime < local_mtime:
                    logging.debug("[*] {} is newer than stored version, scheduling backup".format(file))
                    do_backup = True
                else:
                    logging.debug("[.] {} is up to date.".format(file))
            else:
                logging.debug("[?] {} is missing, scheduling download".format(file))
                threads.append(
                        threading.Thread(
                            target=tahoe.get, 
                            args=(metadata['uri'], file, metadata['mtime'])))
    for file, metadata in local_mtimes.items():
        if file.split(local_dir + os.path.sep)[1] not in remote_mtimes:
            # TODO: Distinguish between local files that haven't been stored
            # and intentional (remote) deletions (perhaps only polled syncs 
            # should delete?)
            if not '.gridsync-versions' in file.split(local_dir + os.path.sep)[1]:
                logging.debug("[!] {} isn't stored, scheduling backup".format(file))
                do_backup = True
    [t.start() for t in threads]
    [t.join() for t in threads]
    if do_backup:
        tahoe.backup(local_dir, remote_dircap)
    tahoe.parent.sync_state -= 1
