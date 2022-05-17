# -*- coding: utf-8 -*-

import json
import logging as log
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import treq
import yaml
from atomicwrites import atomic_write
from twisted.internet.defer import inlineCallbacks
from twisted.internet.error import ConnectError

from gridsync import APP_NAME
from gridsync import settings as global_settings
from gridsync.config import Config
from gridsync.crypto import trunchash
from gridsync.errors import TahoeCommandError, TahoeWebError
from gridsync.magic_folder import MagicFolder
from gridsync.monitor import Monitor
from gridsync.msg import critical
from gridsync.news import NewscapChecker
from gridsync.rootcap import RootcapManager
from gridsync.streamedlogs import StreamedLogs
from gridsync.supervisor import Supervisor
from gridsync.system import SubprocessProtocol, which
from gridsync.types import TwistedDeferred
from gridsync.util import Poller
from gridsync.zkapauthorizer import PLUGIN_NAME as ZKAPAUTHZ_PLUGIN_NAME
from gridsync.zkapauthorizer import ZKAPAuthorizer


def is_valid_furl(furl):
    return re.match(r"^pb://[a-z2-7]+@[a-zA-Z0-9\.:,-]+:\d+/[a-z2-7]+$", furl)


def get_nodedirs(basedir):
    nodedirs = []
    try:
        for filename in os.listdir(basedir):
            filepath = os.path.join(basedir, filename)
            confpath = os.path.join(filepath, "tahoe.cfg")
            if os.path.isdir(filepath) and os.path.isfile(confpath):
                log.debug("Found nodedir: %s", filepath)
                nodedirs.append(filepath)
    except OSError:
        pass
    return sorted(nodedirs)


class Tahoe:

    """
    :ivar zkap_auth_required: ``True`` if the node is configured to use
        ZKAPAuthorizer and spend ZKAPs for storage operations, ``False``
        otherwise.

    :ivar nodeurl: ``None`` until the Tahoe-LAFS child process is running,
        then a string giving the root of the node's HTTP API.
    """

    STOPPED = 0
    STARTING = 1
    STARTED = 2
    STOPPING = 3

    def __init__(self, nodedir=None, executable=None, reactor=None):
        if reactor is None:
            from twisted.internet import reactor
        self.executable = executable
        if nodedir:
            self.nodedir = os.path.expanduser(nodedir)
        else:
            self.nodedir = os.path.join(os.path.expanduser("~"), ".tahoe")
        self.servers_yaml_path = os.path.join(
            self.nodedir, "private", "servers.yaml"
        )
        self.config = Config(os.path.join(self.nodedir, "tahoe.cfg"))
        self.pidfile = os.path.join(self.nodedir, f"{APP_NAME}-tahoe.pid")
        self.nodeurl = None
        self.shares_happy = 0
        self.name = os.path.basename(self.nodedir)
        self.api_token = None
        self.use_tor = False
        self.monitor = Monitor(self)
        logs_maxlen = None
        debug_settings = global_settings.get("debug")
        if debug_settings:
            log_maxlen = debug_settings.get("log_maxlen")
            if log_maxlen is not None:
                logs_maxlen = int(log_maxlen)
        self.streamedlogs = StreamedLogs(reactor, logs_maxlen)
        self.state = Tahoe.STOPPED
        self.newscap = ""
        self.newscap_checker = NewscapChecker(self)
        self.settings: dict = {}
        self.recovery_key_exported = False

        self.zkapauthorizer = ZKAPAuthorizer(self)
        self.zkap_auth_required: bool = False

        self.storage_furl: str = ""
        self.rootcap_manager = RootcapManager(self)
        self.magic_folder = MagicFolder(self, logs_maxlen=logs_maxlen)

        self.monitor.zkaps_redeemed.connect(self.zkapauthorizer.backup_zkaps)  # XXX
        self.magic_folder.monitor.files_updated.connect(
            lambda *args: self.zkapauthorizer.update_zkap_checkpoint()  # XXX
        )
        self.supervisor = Supervisor(pidfile=Path(self.pidfile))

        # TODO: Replace with "readiness" API?
        # https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2844
        @inlineCallbacks
        def poll():
            ready = yield self.is_ready()
            if ready:
                log.debug('Connected to "%s"', self.name)
            else:
                log.debug('Connecting to "%s"...', self.name)
            return ready

        self._ready_poller = Poller(reactor, poll, 0.2)

    def load_newscap(self):
        news_settings = global_settings.get("news:{}".format(self.name))
        if news_settings:
            newscap = news_settings.get("newscap")
            if newscap:
                self.newscap = newscap
                return
        try:
            self.newscap = Path(self.nodedir, "private", "newscap").read_text(
                encoding="utf-8"
            )
        except OSError:
            pass

    def config_set(self, section, option, value):
        self.config.set(section, option, value)

    def config_get(self, section, option):
        return self.config.get(section, option)

    def save_settings(self, settings: dict) -> None:
        with atomic_write(
            str(Path(self.nodedir, "private", "settings.json")), overwrite=True
        ) as f:
            f.write(json.dumps(settings))

        rootcap = settings.get("rootcap")
        if rootcap:
            self.rootcap_manager.set_rootcap(rootcap, overwrite=True)

        newscap = settings.get("newscap")
        if newscap:
            with atomic_write(
                str(Path(self.nodedir, "private", "newscap")), overwrite=True
            ) as f:
                f.write(newscap)

        convergence = settings.get("convergence")
        if convergence:
            with atomic_write(
                str(Path(self.nodedir, "private", "convergence")),
                overwrite=True,
            ) as f:
                f.write(convergence)

    def load_settings(self):
        try:
            with open(
                Path(self.nodedir, "private", "settings.json"),
                encoding="utf-8",
            ) as f:
                settings = json.loads(f.read())
        except FileNotFoundError:
            settings = {}
        settings["nickname"] = self.name
        settings["shares-needed"] = self.config_get("client", "shares.needed")
        settings["shares-happy"] = self.config_get("client", "shares.happy")
        settings["shares-total"] = self.config_get("client", "shares.total")
        introducer = self.config_get("client", "introducer.furl")
        if introducer:
            settings["introducer"] = introducer
        storage_servers = self.get_storage_servers()
        if storage_servers:
            settings["storage"] = storage_servers
        icon_path = os.path.join(self.nodedir, "icon")
        icon_url_path = icon_path + ".url"
        if os.path.exists(icon_url_path):
            with open(icon_url_path, encoding="utf-8") as f:
                settings["icon_url"] = f.read().strip()
        if Path(self.nodedir, "private", "recovery_key_exported").exists():
            self.recovery_key_exported = True
        self.load_newscap()
        if self.newscap:
            settings["newscap"] = self.newscap
        if not settings.get("rootcap"):
            settings["rootcap"] = self.get_rootcap()
        zkap_unit_name = settings.get("zkap_unit_name", "")
        if zkap_unit_name:
            self.zkapauthorizer.zkap_unit_name = zkap_unit_name
        self.zkapauthorizer.zkap_unit_multiplier = settings.get(
            "zkap_unit_multiplier", 1
        )
        self.zkapauthorizer.zkap_payment_url_root = settings.get(
            "zkap_payment_url_root", ""
        )
        # TODO: Verify integrity? Support 'icon_base64'?
        self.settings = settings

    def get_settings(self, include_secrets=False):
        if not self.settings:
            self.load_settings()
        settings = dict(self.settings)
        if include_secrets:
            settings["rootcap"] = self.get_rootcap()
            settings["convergence"] = (
                Path(self.nodedir, "private", "convergence")
                .read_text(encoding="utf-8")
                .strip()
            )
        else:
            try:
                del settings["rootcap"]
            except KeyError:
                pass
            try:
                del settings["convergence"]
            except KeyError:
                pass
        return settings

    def export(self, dest, include_secrets=False):
        log.debug("Exporting settings to '%s'...", dest)
        settings = self.get_settings(include_secrets)
        if self.use_tor:
            settings["hide-ip"] = True
        with atomic_write(dest, mode="w", overwrite=True) as f:
            f.write(json.dumps(settings))
        log.debug("Exported settings to '%s'", dest)

    def _read_servers_yaml(self):
        try:
            with open(self.servers_yaml_path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        except OSError:
            return {}

    def get_storage_servers(self):
        yaml_data = self._read_servers_yaml()
        if not yaml_data:
            return {}
        storage = yaml_data.get("storage")
        if not storage or not isinstance(storage, dict):
            return {}
        results = {}
        for server, server_data in storage.items():
            ann = server_data.get("ann")
            if not ann:
                continue
            results[server] = {
                "anonymous-storage-FURL": ann.get("anonymous-storage-FURL")
            }
            nickname = ann.get("nickname")
            if nickname:
                results[server]["nickname"] = nickname
            storage_options = ann.get("storage-options")
            if storage_options:
                results[server]["storage-options"] = storage_options
        return results

    def _configure_storage_plugins(self, storage_options: List[dict]) -> None:
        for options in storage_options:
            if not isinstance(options, dict):
                log.warning(
                    "Skipping unknown storage plugin option: %s", options
                )
                continue
            config = storage_options_to_config(options)
            if config is None:
                log.warning(
                    "Skipping unknown storage plugin option: %s", options
                )
            else:
                self.config.save(config)

    def add_storage_server(
        self, server_id, furl, nickname=None, storage_options=None
    ):
        log.debug("Adding storage server: %s...", server_id)
        yaml_data = self._read_servers_yaml()
        if not yaml_data or not yaml_data.get("storage"):
            yaml_data["storage"] = {}
        yaml_data["storage"][server_id] = {
            "ann": {"anonymous-storage-FURL": furl}
        }
        if nickname:
            yaml_data["storage"][server_id]["ann"]["nickname"] = nickname
        if storage_options:
            yaml_data["storage"][server_id]["ann"][
                "storage-options"
            ] = storage_options
            self._configure_storage_plugins(storage_options)
        with atomic_write(
            self.servers_yaml_path, mode="w", overwrite=True
        ) as f:
            f.write(yaml.safe_dump(yaml_data, default_flow_style=False))
        log.debug("Added storage server: %s", server_id)

    def add_storage_servers(self, storage_servers):
        for server_id, data in storage_servers.items():
            nickname = data.get("nickname")
            storage_options = data.get("storage-options")
            furl = data.get("anonymous-storage-FURL")
            if furl:
                self.add_storage_server(
                    server_id, furl, nickname, storage_options
                )
            else:
                log.warning("No storage fURL provided for %s!", server_id)

    def line_received(self, line):
        # TODO: Connect to Core via Qt signals/slots?
        log.debug("[%s] >>> %s", self.name, line)

    @inlineCallbacks
    def command(self, args, callback_trigger=None):
        from twisted.internet import reactor

        if not self.executable:
            self.executable = which("tahoe")
        args = [self.executable, "-d", self.nodedir] + args
        env = os.environ
        env["PYTHONUNBUFFERED"] = "1"
        log.debug("Executing: %s...", " ".join(args))
        protocol = SubprocessProtocol(
            callback_triggers=[callback_trigger],
            stdout_line_collector=self.line_received,
        )
        transport = yield reactor.spawnProcess(
            protocol, self.executable, args=args, env=env
        )
        try:
            output = yield protocol.done
        except Exception as e:  # pylint: disable=broad-except
            raise TahoeCommandError(f"{type(e).__name__}: {str(e)}") from e
        if callback_trigger:
            return transport.pid
        return output

    @inlineCallbacks
    def create_node(self, **kwargs):
        if os.path.exists(self.nodedir):
            raise FileExistsError(
                "Nodedir already exists: {}".format(self.nodedir)
            )
        args = ["create-node", "--webport=tcp:0:interface=127.0.0.1"]
        for key, value in kwargs.items():
            if key in (
                "nickname",
                "introducer",
                "shares-needed",
                "shares-happy",
                "shares-total",
                "listen",
                "location",
                "port",
            ):
                args.extend([f"--{key}", str(value)])
            elif key in ("needed", "happy", "total"):
                args.extend([f"--shares-{key}", str(value)])
            elif key in ("hide-ip", "no-storage"):
                args.append(f"--{key}")
        yield self.command(args)
        storage_servers = kwargs.get("storage")
        if storage_servers and isinstance(storage_servers, dict):
            self.add_storage_servers(storage_servers)

    @inlineCallbacks
    def create_client(self, **kwargs):
        kwargs["no-storage"] = True
        kwargs["listen"] = "none"
        yield self.create_node(**kwargs)

    def is_storage_node(self) -> bool:
        if self.storage_furl:
            return True
        return False

    @inlineCallbacks
    def stop(self):
        log.debug('Stopping "%s" tahoe client...', self.name)
        if not os.path.isfile(self.pidfile):
            log.error('No "twistd.pid" file found in %s', self.nodedir)
            return
        self.state = Tahoe.STOPPING
        self.streamedlogs.stop()
        if self.rootcap_manager.lock.locked:
            log.warning(
                "Delaying stop operation; "
                "another operation is trying to modify the rootcap..."
            )
            yield self.rootcap_manager.lock.acquire()
            yield self.rootcap_manager.lock.release()
            log.debug("Lock released; resuming stop operation...")
        if not self.is_storage_node():
            yield self.magic_folder.stop()
        yield self.supervisor.stop()
        self.state = Tahoe.STOPPED
        log.debug('Finished stopping "%s" tahoe client', self.name)

    def get_streamed_log_messages(self):
        """
        Return a ``deque`` containing all buffered log messages.

        :return: A ``deque`` where each element is a UTF-8 & JSON encoded
            ``bytes`` object giving a single log event with older events
            appearing first.
        """
        return self.streamedlogs.get_streamed_log_messages()

    def _on_started(self) -> None:
        self.load_settings()

        with open(
            os.path.join(self.nodedir, "node.url"), encoding="utf-8"
        ) as f:
            self.set_nodeurl(f.read().strip())
        token_file = os.path.join(self.nodedir, "private", "api_auth_token")
        with open(token_file, encoding="utf-8") as f:
            self.api_token = f.read().strip()
        self.shares_happy = int(self.config_get("client", "shares.happy"))
        self.load_newscap()
        self.newscap_checker.start()
        storage_furl_path = Path(self.nodedir, "private", "storage.furl")
        if storage_furl_path.exists():
            self.storage_furl = storage_furl_path.read_text(
                encoding="utf-8"
            ).strip()

        self.streamedlogs.stop()
        self.streamedlogs.start(self.nodeurl, self.api_token)

        self.state = Tahoe.STARTED

        self.scan_storage_plugins()

        if not self.is_storage_node():
            self.magic_folder.start()

    @inlineCallbacks
    def start(self):
        log.debug('Starting "%s" tahoe client...', self.name)
        self.state = Tahoe.STARTING
        self.monitor.start()
        tcp = self.config_get("connections", "tcp")
        if tcp and tcp.lower() == "tor":
            self.use_tor = True
        if self.config_get(
            f"storageclient.plugins.{ZKAPAUTHZ_PLUGIN_NAME}",
            "ristretto-issuer-root-url",
        ):
            self.zkap_auth_required = True
        if self.zkap_auth_required:
            default_token_count = self.config_get(
                f"storageclient.plugins.{ZKAPAUTHZ_PLUGIN_NAME}",
                "default-token-count",
            )
            if default_token_count:
                self.zkapauthorizer.zkap_batch_size = int(default_token_count)

        if not self.executable:
            self.executable = which("tahoe")
        try:
            results = yield self.supervisor.start(
                [self.executable, "-d", self.nodedir, "run"],
                started_trigger="client running",
                stdout_line_collector=self.line_received,
                process_started_callback=self._on_started,
            )
        except Exception as exc:  # pylint: disable=broad-except
            critical(
                f"Error starting Tahoe-LAFS gateway for {self.name}",
                "A critical error occurred when attempting to start the "
                f'Tahoe-LAFS gateway for "{self.name}". {APP_NAME} will '
                'now exit.\n\nClick "Show Details..." for more information.',
                str(exc),
            )
            return
        pid, _ = results
        log.debug(
            'Finished starting "%s" tahoe client (pid: %i)', self.name, pid
        )

    def set_nodeurl(self, nodeurl):
        """
        Specify the location of the Tahoe-LAFS web API.

        :param str nodeurl: A text string giving the URI root of the web API.
        """
        self.nodeurl = nodeurl

    @inlineCallbacks
    def get_grid_status(self):
        if not self.nodeurl:
            return None
        try:
            resp = yield treq.get(self.nodeurl + "?t=json")
        except ConnectError:
            return None
        if resp.code == 200:
            content = yield treq.content(resp)
            content = json.loads(content.decode("utf-8"))
            servers_connected = 0
            servers_known = 0
            available_space = 0
            if "servers" in content:
                servers = content["servers"]
                servers_known = len(servers)
                for server in servers:
                    if server["connection_status"].startswith("Connected"):
                        servers_connected += 1
                        if server["available_space"]:
                            available_space += server["available_space"]
            return servers_connected, servers_known, available_space
        return None

    @inlineCallbacks
    def get_connected_servers(self):
        if not self.nodeurl:
            return None
        try:
            resp = yield treq.get(self.nodeurl)
        except ConnectError:
            return None
        if resp.code == 200:
            html = yield treq.content(resp)
            match = re.search(
                "Connected to <span>(.+?)</span>", html.decode("utf-8")
            )
            if match:
                return int(match.group(1))
        return None

    @inlineCallbacks
    def is_ready(self):
        if not self.shares_happy:
            return False
        connected_servers = yield self.get_connected_servers()
        return bool(
            connected_servers and connected_servers >= self.shares_happy
        )

    def await_ready(self):
        return self._ready_poller.wait_for_completion()

    @inlineCallbacks
    def mkdir(self, parentcap=None, childname=None):
        yield self.await_ready()
        url = self.nodeurl + "uri"
        params = {"t": "mkdir"}
        if parentcap and childname:
            url += "/" + parentcap
            params["name"] = childname
        resp = yield treq.post(url, params=params)
        if resp.code == 200:
            content = yield treq.content(resp)
            return content.decode("utf-8").strip()
        raise TahoeWebError(
            "Error creating Tahoe-LAFS directory: {}".format(resp.code)
        )

    @inlineCallbacks
    def diminish(self, cap: str) -> TwistedDeferred[str]:
        output = yield self.get_json(cap)
        return output[1]["ro_uri"]

    @inlineCallbacks
    def create_rootcap(self) -> TwistedDeferred[str]:
        rootcap = yield self.rootcap_manager.create_rootcap()
        return rootcap

    @inlineCallbacks
    def upload(
        self, local_path: str, dircap: str = "", mutable: bool = False
    ) -> TwistedDeferred[str]:
        if dircap:
            filename = Path(local_path).name
            url = f"{self.nodeurl}uri/{dircap}/{filename}"
        else:
            url = f"{self.nodeurl}uri"
        if mutable:
            url = f"{url}?format=MDMF"
        log.debug("Uploading %s...", local_path)
        yield self.await_ready()
        with open(local_path, "rb") as f:
            resp = yield treq.put(url, f)
        if resp.code in (200, 201):
            content = yield treq.content(resp)
            log.debug("Successfully uploaded %s", local_path)
            return content.decode("utf-8")
        content = yield treq.content(resp)
        raise TahoeWebError(content.decode("utf-8"))

    @inlineCallbacks
    def download(self, cap, local_path):
        log.debug("Downloading %s...", local_path)
        yield self.await_ready()
        resp = yield treq.get("{}uri/{}".format(self.nodeurl, cap))
        if resp.code == 200:
            with atomic_write(local_path, mode="wb", overwrite=True) as f:
                yield treq.collect(resp, f.write)
            log.debug("Successfully downloaded %s", local_path)
        else:
            content = yield treq.content(resp)
            raise TahoeWebError(content.decode("utf-8"))

    @inlineCallbacks
    def link(self, dircap, childname, childcap):
        dircap_hash = trunchash(dircap)
        childcap_hash = trunchash(childcap)
        log.debug(
            'Linking "%s" (%s) into %s...',
            childname,
            childcap_hash,
            dircap_hash,
        )
        yield self.await_ready()
        resp = yield treq.post(
            "{}uri/{}/?t=uri&name={}&uri={}".format(
                self.nodeurl, dircap, childname, childcap
            )
        )
        if resp.code != 200:
            content = yield treq.content(resp)
            raise TahoeWebError(content.decode("utf-8"))
        log.debug(
            'Done linking "%s" (%s) into %s',
            childname,
            childcap_hash,
            dircap_hash,
        )

    @inlineCallbacks
    def unlink(self, dircap, childname, missing_ok=False):
        dircap_hash = trunchash(dircap)
        log.debug('Unlinking "%s" from %s...', childname, dircap_hash)
        yield self.await_ready()
        resp = yield treq.post(
            "{}uri/{}/?t=unlink&name={}".format(
                self.nodeurl, dircap, childname
            )
        )
        if resp.code == 404 and missing_ok:
            pass
        elif resp.code != 200:
            content = yield treq.content(resp)
            raise TahoeWebError(content.decode("utf-8"))
        log.debug('Done unlinking "%s" from %s', childname, dircap_hash)

    @inlineCallbacks
    def get_json(self, cap):
        if not cap or not self.nodeurl:
            return None
        uri = "{}uri/{}/?t=json".format(self.nodeurl, cap)
        try:
            resp = yield treq.get(uri)
        except ConnectError:
            return None
        if resp.code == 200:
            content = yield treq.content(resp)
            return json.loads(content.decode("utf-8"))
        return None

    @inlineCallbacks
    def ls(
        self,
        cap: str,
        exclude_dirnodes: bool = False,
        exclude_filenodes: bool = False,
    ) -> TwistedDeferred[Optional[Dict[str, dict]]]:
        yield self.await_ready()
        json_output = yield self.get_json(cap)
        if json_output is None:
            return None
        results = {}
        for name, data in json_output[1]["children"].items():
            node_type = data[0]
            if node_type == "dirnode" and exclude_dirnodes:
                continue
            if node_type == "filenode" and exclude_filenodes:
                continue
            data = data[1]
            results[name] = data
            # Include the most "authoritative" capability separately:
            results[name]["cap"] = data.get("rw_uri", data.get("ro_uri", ""))
            results[name]["type"] = node_type
        return results

    def get_rootcap(self) -> str:
        return self.rootcap_manager.get_rootcap()

    @inlineCallbacks
    def scan_storage_plugins(self):
        plugins = []
        log.debug("Scanning for known storage plugins...")
        version = yield self.zkapauthorizer.get_version()
        if version:
            plugins.append(("ZKAPAuthorizer", version))
        if plugins:
            log.debug("Found storage plugins: %s", plugins)
        else:
            log.debug("No storage plugins found")


# The names of all of the optional items in a ZKAPAuthorizer configuration
# section.  These are optional both in the storage options object and the
# tahoe.cfg section.
_ZKAPAUTHZ_OPTIONAL_ITEMS = {
    "pass-value",
    "default-token-count",
    "allowed-public-keys",
    "lease.crawl-interval.mean",
    "lease.crawl-interval.range",
    "lease.min-time-remaining",
}


def storage_options_to_config(options: Dict) -> Optional[Dict]:
    """
    Reshape a storage-options configuration dictionary into a tahoe.cfg
    configuration dictionary.
    """
    name = options.get("name")
    if name == ZKAPAUTHZ_PLUGIN_NAME:
        zkapauthz = {
            "redeemer": "ristretto",
            "ristretto-issuer-root-url": options.get(
                "ristretto-issuer-root-url"
            ),
        }
        zkapauthz.update(
            {
                optional_item: options.get(optional_item)
                for optional_item in _ZKAPAUTHZ_OPTIONAL_ITEMS
                if options.get(optional_item) is not None
            }
        )

        return {
            "client": {
                # TODO: Append name instead of setting/overriding?
                "storage.plugins": name,
            },
            f"storageclient.plugins.{ZKAPAUTHZ_PLUGIN_NAME}": zkapauthz,
        }

    return None
