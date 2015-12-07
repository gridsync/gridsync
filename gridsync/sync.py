# -*- coding: utf-8 -*-

import datetime
import logging
import os
import shutil
import sys

import requests

from twisted.internet import reactor
from twisted.internet.defer import gatherResults
from twisted.internet.task import LoopingCall
from twisted.internet.threads import deferToThread, blockingCallFromThread
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer


class SyncFolder(PatternMatchingEventHandler):
    def __init__(self, local_dir, remote_dircap, tahoe=None,
            ignore_patterns=None):
        _ignore_patterns = ['*.gridsync-versions*', '*.part*',
                '*(conflicted copy *-*-* *-*-*)*']
        if ignore_patterns:
            _ignore_patterns += ignore_patterns
        super(SyncFolder, self).__init__(ignore_patterns=_ignore_patterns)
        if not tahoe:
            from gridsync.tahoe import Tahoe
            tahoe = Tahoe()
        self.tahoe = tahoe
        self.local_dir = os.path.expanduser(local_dir)
        self.remote_dircap = remote_dircap
        self.versions_dir = os.path.join(self.local_dir, '.gridsync-versions')
        self.local_snapshot = 0
        self.filesystem_modified = False
        self.do_backup = False
        self.do_sync = False
        self.sync_state = 0
        self.sync_log = []
        self.keep_versions = 1
        self.local_checker = LoopingCall(self.check_for_changes)
        self.remote_checker = LoopingCall(reactor.callInThread, self.sync)
        logging.debug("{} initialized; "
                "{} <-> {}".format(self, self.local_dir, self.remote_dircap))

    def on_modified(self, event):
        self.filesystem_modified = True
        #try:
        #    reactor.callFromThread(self.local_checker.start, 1)
        #except AssertionError:
        #    return
        reactor.callFromThread(self._start_local_checker)

    def _start_local_checker(self):
        # XXX: For some (qt5reactor-related?) reason, the AssertionError
        # raised by trying to start the (already-running) local_checker timer
        # above won't catch if called from reactor.callFromThread. Why is this?
        try:
            self.local_checker.start(1)
        except AssertionError:
            return

    def check_for_changes(self):
        if self.filesystem_modified:
            self.filesystem_modified = False
        else:
            reactor.callFromThread(self.local_checker.stop)
            reactor.callInThread(self.sync, force_backup=True)

    def start(self):
        try:
            self.remote_dircap_alias = self.tahoe.aliasify(self.remote_dircap)
        except ValueError:
            # TODO: Alert user alias is garbled?
            pass
        except LookupError:
            # TODO: Alert user alias is missing?
            pass
        logging.info("Starting Observer in {}...".format(self.local_dir))
        try:
            self.observer = Observer()
            self.observer.schedule(self, self.local_dir, recursive=True)
            self.observer.start()
        except Exception as error:
            logging.error(error)
        reactor.callFromThread(self.remote_checker.start, 30)

    def _create_conflicted_copy(self, filepath):
        base, extension = os.path.splitext(filepath)
        mtime = int(os.path.getmtime(filepath))
        t = datetime.datetime.fromtimestamp(mtime)
        tag = t.strftime('.(conflicted copy %Y-%m-%d %H-%M-%S)')
        tagged_filepath = base + tag + extension
        logging.debug("Creating conflicted copy of {} {}".format(
                filepath, tagged_filepath))
        os.rename(filepath, tagged_filepath)
        os.utime(tagged_filepath, (-1, mtime))

    def _create_versioned_copy(self, filename, mtime):
        local_filepath = os.path.join(self.local_dir, filename)
        base, extension = os.path.splitext(filename)
        t = datetime.datetime.fromtimestamp(mtime)
        tag = t.strftime('.(%Y-%m-%d %H-%M-%S)')
        newname = base + tag + extension
        versioned_filepath = newname.replace(self.local_dir, self.versions_dir)
        if not os.path.isdir(os.path.dirname(versioned_filepath)):
            os.makedirs(os.path.dirname(versioned_filepath))
        logging.info("Creating {}".format(versioned_filepath))
        shutil.copy2(local_filepath, versioned_filepath)

    def get_local_metadata(self, basedir=None):
        metadata = {}
        if not basedir:
            basedir = self.local_dir
        for root, dirs, files in os.walk(basedir, followlinks=True):
            for name in dirs:
                path = os.path.join(root, name)
                if not path.startswith(self.versions_dir):
                    metadata[path] = {}
            for name in files:
                path = os.path.join(root, name)
                if not path.startswith(self.versions_dir):
                    metadata[path] = {
                        'mtime': int(os.path.getmtime(path)),
                        'size': os.path.getsize(path)}
        return metadata

    def get_remote_metadata(self, dircap, basedir=''):
        metadata = {}
        jobs = []
        logging.debug("Getting remote metadata from {}...".format(dircap))
        url = '{}uri/{}/?t=json'.format(self.tahoe.node_url, dircap)
        received_data = requests.get(url).json()
        for filename, data in received_data[1]['children'].items():
            path = '/'.join([basedir, filename]).strip('/')
            metadata[path] = {
                'uri': data[1]['ro_uri'],
                'mtime': int(data[1]['metadata']['mtime'])}
            if data[0] == 'dirnode':
                jobs.append(deferToThread(self.get_remote_metadata,
                    '/'.join([dircap, filename]), path))
        results = blockingCallFromThread(reactor, gatherResults, jobs)
        for result in results:
            metadata.update(result)
        return metadata


    def sync(self, snapshot=None, force_backup=False):
        if self.sync_state:
            logging.debug("Sync already in progress; queueing to end...")
            self.do_sync = True
            return
        if not snapshot:
            try:
                ls = self.tahoe.ls(self.remote_dircap)
                if not ls:
                    logging.debug("No /Archives found; "
                            "performing (first?) backup...")
                    self.sync_state += 1
                    self.backup(self.local_dir, self.remote_dircap_alias)
                    self.sync_complete(ls)
                    return
            except Exception as error:
                logging.error(error)
                return
            # XXX: It might be preferable to just check the dircap of /Latest/
            pre_sync_archives = self.tahoe.ls(self.remote_dircap + "/Archives")
            available_snapshot = pre_sync_archives[-1]
            if self.local_snapshot == available_snapshot:
                if force_backup:
                    self.sync_state += 1
                    self.backup(self.local_dir, self.remote_dircap_alias)
                    self.sync_complete(pre_sync_archives)
                return
            else:
                snapshot = available_snapshot
        remote_path = self.remote_dircap + '/Archives/' + snapshot
        logging.info("Syncing {} with {}...".format(self.local_dir, snapshot))
        self.sync_state += 1
        self.local_metadata = self.get_local_metadata(self.local_dir)
        self.remote_metadata = self.get_remote_metadata(remote_path)
        # TODO: If tahoe.get_metadata() fails or doesn't contain a
        # valid snapshot, jump to backup?
        jobs = []
        for file, metadata in self.remote_metadata.items():
            if metadata['uri'].startswith('URI:DIR'):
                dirpath = os.path.join(self.local_dir, file)
                if not os.path.isdir(dirpath):
                    logging.info("Creating directory: {}...".format(dirpath))
                    os.makedirs(dirpath)
        for file, metadata in self.remote_metadata.items():
            if not metadata['uri'].startswith('URI:DIR'):
                filepath = os.path.join(self.local_dir, file)
                remote_mtime = metadata['mtime']
                if filepath in self.local_metadata:
                    local_filesize = self.local_metadata[filepath]['size']
                    local_mtime = self.local_metadata[filepath]['mtime']
                    if local_mtime < remote_mtime:
                        logging.debug("[<] {} is older than remote version; "
                                "downloading {}...".format(file, file))
                        if self.keep_versions:
                            self._create_versioned_copy(filepath, local_mtime)
                        jobs.append(deferToThread(self.download,
                            remote_path + '/' + file, filepath, remote_mtime))
                    elif local_mtime > remote_mtime:
                        logging.debug("[>] {} is newer than remote version; "
                                "backup scheduled".format(file)) 
                        self.do_backup = True
                    else:
                        logging.debug("[.] {} is up to date.".format(file))
                else:
                    logging.debug("[?] {} is missing; "
                            "downloading {}...".format(file, file))
                    jobs.append(deferToThread(self.download,
                        remote_path + '/' + file, filepath, remote_mtime))
        for file, metadata in self.local_metadata.items():
            fn = file.split(self.local_dir + os.path.sep)[1]
            if fn not in self.remote_metadata:
                if metadata:
                    recovery_uri = self.tahoe.stored(file, metadata['size'],
                            metadata['mtime'])
                    if recovery_uri:
                        logging.debug("[x] {} removed from latest snapshot; "
                                "deleting local file...".format(file))
                        if self.keep_versions:
                            self._create_versioned_copy(file, local_mtime)
                        try:
                            os.remove(file)
                        except Exception as error:
                            logging.error(error)
                    else:
                        logging.debug("[!] {} isn't stored; "
                            "backup scheduled".format(fn))
                        self.do_backup = True
        blockingCallFromThread(reactor, gatherResults, jobs)
        if self.do_backup:
            self.backup(self.local_dir, self.remote_dircap_alias)
            self.do_backup = False
        if self.do_sync:
            self.sync()
        self.sync_complete(pre_sync_archives)

    def sync_complete(self, pre_sync_archives):
        post_sync_archives = self.tahoe.ls(self.remote_dircap + "/Archives")
        if len(post_sync_archives) - len(pre_sync_archives) <= 1:
            self.local_snapshot = post_sync_archives[-1]
            logging.info("Synchronized {} with {}".format(
                self.local_dir, self.local_snapshot))
        else:
            logging.warn("Remote state changed during sync")
            # TODO: Re-sync/merge overlooked snapshot
        self.sync_state -= 1

    def download(self, remote_uri, local_filepath, mtime=None):
        url = self.tahoe.node_url + 'uri/' + remote_uri
        download_path = local_filepath + '.part'
        #if os.path.exists(download_path):
            # XXX: Resuming may not be a good idea, as the existent (local)
            # parts may no longer be present in the latest (remote) version of
            # the file. Perhaps an integrity/filecap check should be required?
        #    size = os.path.getsize(download_path)
        #    logging.debug("Partial download of {} found; resuming byte {}..."\
        #            .format(local_filepath, size))
        #    request.headers['Range'] = 'bytes={}-'.format(size)
        # TODO: Handle exceptions..
        if os.path.isfile(download_path) or os.path.isdir(download_path):
            raise OSError("File exists: '{}'".format(download_path))
        r = requests.get(url, stream=True)
        r.raise_for_status()
        recv = 0
        with open(download_path, 'wb') as f:
            for chunk in r.iter_content(4096):
                f.write(chunk)
                recv += len(chunk)
        if os.path.isfile(local_filepath):
            local_filesize = os.path.getsize(local_filepath)
            if not self.tahoe.stored(file, local_filesize, mtime):
                self._create_conflicted_copy(local_filepath)
        os.rename(download_path, local_filepath)
        if mtime:
            os.utime(local_filepath, (-1, mtime))
        self.sync_log.append("Downloaded {}".format(
            local_filepath.lstrip(self.local_dir)))
        return recv

    def backup(self, local_dir, remote_dircap):
        excludes = ['--exclude=' + x for x in self.ignore_patterns]
        output = self.tahoe.command(['backup', '-v'] + excludes + [local_dir,
                remote_dircap])
        for line in output.split('\n'):
            if line.startswith('uploading'):
                filename = line[11:][:-3].lstrip(self.local_dir)
                self.sync_log.append("Uploaded {}".format(filename))

    def stop(self):
        logging.info("Stopping Observer in {}...".format(self.local_dir))
        try:
            self.observer.stop()
            self.observer.join()
        except Exception as error:
            logging.error(error)
        self.remote_checker.stop()

