# -*- coding: utf-8 -*-

import json
import logging as log
import os
import re
import shutil
from pathlib import Path
from typing import Optional, Union, cast

import treq
import yaml
from atomicwrites import atomic_write
from twisted.internet.defer import Deferred
from twisted.internet.error import ConnectError
from twisted.internet.interfaces import IReactorTime

from gridsync import APP_NAME, grid_settings
from gridsync import settings as global_settings
from gridsync.capabilities import diminish
from gridsync.config import Config
from gridsync.crypto import trunchash
from gridsync.errors import (
    TahoeCommandError,
    TahoeWebError,
    UpgradeRequiredError,
)
from gridsync.log import MultiFileLogger, NullLogger
from gridsync.magic_folder import MagicFolder
from gridsync.monitor import Monitor
from gridsync.msg import critical
from gridsync.news import NewscapChecker
from gridsync.rootcap import RootcapManager
from gridsync.supervisor import Supervisor
from gridsync.system import SubprocessProtocol, which
from gridsync.util import Poller
from gridsync.websocket import WebSocketReaderService
from gridsync.zkapauthorizer import PLUGIN_NAME as ZKAPAUTHZ_PLUGIN_NAME
from gridsync.zkapauthorizer import ZKAPAuthorizer


def is_valid_furl(furl: str) -> bool:
    if re.match(r"^pb://[a-z2-7]+@[a-zA-Z0-9\.:,-]+:\d+/[a-z2-7]+$", furl):
        return True
    return False


def has_legacy_magic_folder(nodedir: Path) -> bool:
    config = Config(str(nodedir / "tahoe.cfg")).load()
    if "magic_folder" in config:
        return True
    return False


def has_legacy_zkapauthorizer(nodedir: Path) -> bool:
    config = Config(str(nodedir / "tahoe.cfg")).load()
    if "storageclient.plugins.privatestorageio-zkapauthz-v1" in config:
        return True
    storage_plugins = config.get("client", {}).get("storage.plugins")
    if storage_plugins and "privatestorageio-zkapauthz-v1" in storage_plugins:
        return True
    return False


def get_nodedirs(basedir: str) -> list:
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

    :ivar nodeurl: a string giving the root of the node's HTTP API.
    """

    STOPPED = 0
    STARTING = 1
    STARTED = 2
    STOPPING = 3

    def __init__(
        self,
        nodedir: str = "",
        executable: str = "",
        reactor: Optional[IReactorTime] = None,
        enable_logging: bool = True,
    ) -> None:
        if reactor is None:
            from twisted.internet import reactor as reactor_

            # To avoid mypy "assignment" error ("expression has type Module")
            reactor = cast(IReactorTime, reactor_)
        self._reactor = reactor
        self.executable = executable
        if nodedir:
            self.nodedir = os.path.expanduser(nodedir)
        else:
            self.nodedir = os.path.join(os.path.expanduser("~"), ".tahoe")
        self.servers_yaml_path = os.path.join(
            self.nodedir, "private", "servers.yaml"
        )
        self.config = Config(os.path.join(self.nodedir, "tahoe.cfg"))
        self.pidfile = os.path.join(self.nodedir, "running.process")
        self.nodeurl: str = ""
        self.api_token: str = ""
        self.shares_happy = 0
        self.name = os.path.basename(self.nodedir)
        self.use_tor = False
        self.monitor = Monitor(self)
        self.state = Tahoe.STOPPED
        self.newscap = ""
        self.newscap_checker = NewscapChecker(self)
        self.settings: dict = {}
        self.recovery_key_exported = False

        self.zkapauthorizer = ZKAPAuthorizer(self)
        self.zkap_auth_required: bool = False

        self.storage_furl: str = ""
        self.rootcap_manager = RootcapManager(self)
        self.magic_folder = MagicFolder(self)

        self.supervisor = Supervisor(Path(self.pidfile))

        # TODO: Replace with "readiness" API?
        # https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2844
        async def poll() -> bool:
            ready = await self.is_ready()
            if ready:
                log.debug('Connected to "%s"', self.name)
            else:
                log.debug('Connecting to "%s"...', self.name)
            return ready

        self._ready_poller = Poller(reactor, poll, 0.2)

        self.logger: Union[MultiFileLogger, NullLogger]
        if enable_logging:
            self.logger = MultiFileLogger(f"{self.name}.Tahoe-LAFS")
        else:
            self.logger = NullLogger()

        self._ws_reader: Optional[WebSocketReaderService] = None

    def _log_stdout_message(self, message: str) -> None:
        self.logger.log("stdout", message)

    def _log_stderr_message(self, message: str) -> None:
        self.logger.log("stderr", message)

    def _log_eliot_message(self, message: str) -> None:
        try:
            message = json.dumps(json.loads(message), sort_keys=True)
        except json.decoder.JSONDecodeError:
            log.warning("Error decoding JSON message: %s", message)
            return
        self.logger.log("eliot", message, omit_fmt=True)

    def load_newscap(self) -> None:
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

    def config_set(self, section: str, option: str, value: str) -> None:
        self.config.set(section, option, value)

    def config_get(self, section: str, option: str) -> Optional[str]:
        return self.config.get(section, option)

    def save_settings(self, settings: dict) -> None:
        with atomic_write(
            str(Path(self.nodedir, "private", "settings.json")), overwrite=True
        ) as f:
            f.write(json.dumps(settings))

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

    def load_settings(self) -> None:
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

    def get_settings(self, include_secrets: bool = False) -> dict:
        if not self.settings:
            self.load_settings()
        settings = dict(self.settings)

        def _safe_del(dictionary: dict, key: str) -> None:
            try:
                del dictionary[key]
            except KeyError:
                pass

        if include_secrets:
            rootcap = self.get_rootcap()
            if rootcap:
                settings["rootcap"] = diminish(rootcap)
            else:
                _safe_del(settings, "rootcap")
            try:
                settings["convergence"] = (
                    Path(self.nodedir, "private", "convergence")
                    .read_text(encoding="utf-8")
                    .strip()
                )
            except FileNotFoundError:
                _safe_del(settings, "convergence")
        else:
            _safe_del(settings, "rootcap")
            _safe_del(settings, "convergence")
        return settings

    def export(self, dest: str, include_secrets: bool = False) -> None:
        log.debug("Exporting settings to '%s'...", dest)
        settings = self.get_settings(include_secrets)
        if self.use_tor:
            settings["hide-ip"] = True
        with atomic_write(dest, mode="w", overwrite=True) as f:
            f.write(json.dumps(settings))
        log.debug("Exported settings to '%s'", dest)

    def _read_servers_yaml(
        self,
        yaml_filepath: Optional[str] = None,
    ) -> dict:
        if not yaml_filepath:
            yaml_filepath = self.servers_yaml_path
        try:
            with open(yaml_filepath, encoding="utf-8") as f:
                return yaml.safe_load(f)
        except OSError:
            return {}

    def get_storage_servers(
        self,
        yaml_filepath: Optional[str] = None,
    ) -> dict:
        if not yaml_filepath:
            yaml_filepath = self.servers_yaml_path
        yaml_data = self._read_servers_yaml(yaml_filepath)
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

    def _configure_storage_plugins(self, storage_options: list[dict]) -> None:
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

    def add_storage_server(  # pylint: disable=too-many-arguments
        self,
        server_id: str,
        furl: str,
        nickname: Optional[str] = None,
        storage_options: Optional[list[dict]] = None,
        yaml_filepath: Optional[str] = None,
    ) -> None:
        if not yaml_filepath:
            yaml_filepath = self.servers_yaml_path
        log.debug("Adding storage server: %s...", server_id)
        yaml_data = self._read_servers_yaml(yaml_filepath)
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
        with atomic_write(yaml_filepath, mode="w", overwrite=True) as f:
            f.write(yaml.safe_dump(yaml_data, default_flow_style=False))
        log.debug("Added storage server: %s", server_id)

    def add_storage_servers(
        self,
        storage_servers: dict,
        yaml_filepath: Optional[str] = None,
    ) -> None:
        if not yaml_filepath:
            yaml_filepath = self.servers_yaml_path
        for server_id, data in storage_servers.items():
            nickname = data.get("nickname")
            storage_options = data.get("storage-options")
            furl = data.get("anonymous-storage-FURL")
            if furl:
                self.add_storage_server(
                    server_id, furl, nickname, storage_options, yaml_filepath
                )
            else:
                log.warning("No storage fURL provided for %s!", server_id)

    async def command(self, args: list[str]) -> str:
        if not self.executable:
            self.executable = which("tahoe")
        args = [self.executable, "-d", self.nodedir] + args
        env = os.environ
        env["PYTHONUNBUFFERED"] = "1"
        log.debug("Executing: %s...", " ".join(args))
        protocol = SubprocessProtocol(
            stdout_line_collector=self._log_stdout_message,
            stderr_line_collector=self._log_stderr_message,
        )
        self._reactor.spawnProcess(
            protocol, self.executable, args=args, env=env
        )
        try:
            output = await protocol.done
        except Exception as e:  # pylint: disable=broad-except
            raise TahoeCommandError(f"{type(e).__name__}: {str(e)}") from e
        return output

    async def version(self) -> str:
        output = await self.command(["--version"])
        line = output.split("\n")[0]
        return line.lstrip("tahoe-lafs :").lstrip("tahoe-lafs/")

    async def create_node(self, settings: dict) -> None:
        if os.path.exists(self.nodedir):
            raise FileExistsError(
                "Nodedir already exists: {}".format(self.nodedir)
            )
        args = ["create-node", "--webport=tcp:0:interface=127.0.0.1"]
        for key, value in settings.items():
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
        await self.command(args)
        storage_servers = settings.get("storage")
        if storage_servers and isinstance(storage_servers, dict):
            self.add_storage_servers(storage_servers)

    async def create_client(self, settings: dict) -> None:
        settings["no-storage"] = True
        settings["listen"] = "none"
        await self.create_node(settings)

    def is_storage_node(self) -> bool:
        if self.storage_furl:
            return True
        return False

    async def stop(self) -> None:
        log.debug('Stopping "%s" tahoe client...', self.name)
        self.state = Tahoe.STOPPING
        if self._ws_reader:
            self._ws_reader.stop()
            self._ws_reader = None
        if self.rootcap_manager.lock.locked:
            log.warning(
                "Delaying stop operation; "
                "another operation is trying to modify the rootcap..."
            )
            await self.rootcap_manager.lock.acquire()
            self.rootcap_manager.lock.release()
            log.debug("Lock released; resuming stop operation...")
        if not self.is_storage_node():
            await self.magic_folder.stop()
        await self.supervisor.stop()
        self.state = Tahoe.STOPPED
        log.debug('Finished stopping "%s" tahoe client', self.name)

    def get_log(self, name: str) -> str:
        return self.logger.read_log(name)

    def _on_started(self) -> None:
        self.load_settings()

        with open(
            os.path.join(self.nodedir, "node.url"), encoding="utf-8"
        ) as f:
            self.set_nodeurl(f.read().strip())
        token_file = os.path.join(self.nodedir, "private", "api_auth_token")
        with open(token_file, encoding="utf-8") as f:
            self.api_token = f.read().strip()
        shares_happy = self.config_get("client", "shares.happy")
        if shares_happy:
            self.shares_happy = int(shares_happy)
        self.load_newscap()
        self.newscap_checker.start()
        storage_furl_path = Path(self.nodedir, "private", "storage.furl")
        if storage_furl_path.exists():
            self.storage_furl = storage_furl_path.read_text(
                encoding="utf-8"
            ).strip()

        self._ws_reader = WebSocketReaderService(
            self.nodeurl.replace("http://", "ws://") + "/private/logs/v1",
            headers={"Authorization": f"tahoe-lafs {self.api_token}"},
            collector=self._log_eliot_message,
            reactor=self._reactor,
        )
        self._ws_reader.start()

        self.state = Tahoe.STARTED

        # XXX Should something wait on this?
        Deferred.fromCoroutine(self.scan_storage_plugins())

        if not self.is_storage_node():
            # XXX Should something wait on this?
            Deferred.fromCoroutine(self.magic_folder.start())

    def _remove_twistd_pid(self) -> None:
        # On non-Windows systems, Twisted/twistd will create its own
        # pidfile for tahoe processes and refuse to (re)start tahoe
        # if the pid number in the file matches *any* running process,
        # irrespective of the name of that process. Gridsync's
        # Supervisor, however, also creates/manages pidfiles for its
        # processes (including on Windows!) but, unlike twistd, will
        # include and check/verify the name of the process attached to
        # the pid in the pidfile and determine staleness accordingly
        # (i.e., by killing/restarting the process if the name actually
        # corresponds to that of the process it is supposed to be
        # managing, or by removing the pidfile if it does not).
        # Removing the "twistd.pid" file thus avoids the situation in
        # which tahoe will refuse to (re)start because it terminated
        # uncleanly previously and some other process has since begun
        # using the same pid contained in that pidfile. Also, Windows.
        Path(self.nodedir, "twistd.pid").unlink(missing_ok=True)

    def apply_connection_settings(self, settings: dict) -> None:
        tahoe_cfg = os.path.join(self.nodedir, "tahoe.cfg")
        tahoe_cfg_tmp = os.path.join(self.nodedir, "tahoe.cfg.tmp")
        shutil.copy2(tahoe_cfg, tahoe_cfg_tmp)

        config = Config(tahoe_cfg_tmp)

        hide_ip = settings.get("hide-ip")
        if hide_ip:
            config.set("node", "reveal-ip-address", "false")

        introducer_furl = settings.get("introducer")
        if introducer_furl:
            config.set("client", "introducer.furl", introducer_furl)

        shares_needed = settings.get("shares-needed", settings.get("needed"))
        if shares_needed:
            config.set("client", "shares.needed", shares_needed)

        shares_happy = settings.get("shares-happy", settings.get("happy"))
        if shares_happy:
            config.set("client", "shares.happy", shares_happy)

        shares_total = settings.get("shares-total", settings.get("total"))
        if shares_total:
            config.set("client", "shares.total", shares_total)

        servers_yaml = os.path.join(self.nodedir, "private", "servers.yaml")
        servers_yaml_tmp = os.path.join(
            self.nodedir, "private", "servers.yaml.tmp"
        )
        Path(servers_yaml_tmp).unlink(missing_ok=True)

        storage_servers = settings.get("storage")
        if storage_servers and isinstance(storage_servers, dict):
            self.add_storage_servers(storage_servers, servers_yaml_tmp)

        shutil.move(tahoe_cfg_tmp, tahoe_cfg)
        shutil.move(servers_yaml_tmp, servers_yaml)

    def _verify_configuration(self) -> None:
        nodedir = Path(self.nodedir)
        if has_legacy_magic_folder(nodedir):
            raise UpgradeRequiredError(
                f'The Tahoe-LAFS node directory ("{str(nodedir.resolve())}") '
                'is configured to use the Tahoe-LAFS "magic-folder" feature '
                "but this feature was removed in Tahoe-LAFS version 1.15."
            )
        if has_legacy_zkapauthorizer(nodedir):
            raise UpgradeRequiredError(
                f'The Tahoe-LAFS node directory ("{str(nodedir.resolve())}") '
                "is configured to use an older version of the ZKAPAuthorizer "
                'plugin ("v1") that is incompatible with the current version.'
            )
        settings = grid_settings.get(self.name)
        if settings:
            # XXX/TODO: Perhaps this should only be called if these settings
            # differ from those that were previously written in the nodedir?
            self.apply_connection_settings(settings)

    async def start(self) -> None:
        self._verify_configuration()
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
            results = await self.supervisor.start(
                [self.executable, "-d", self.nodedir, "run"],
                started_trigger="client running",
                stdout_line_collector=self._log_stdout_message,
                stderr_line_collector=self._log_stderr_message,
                call_before_start=self._remove_twistd_pid,
                call_after_start=self._on_started,
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

    def set_nodeurl(self, nodeurl: str) -> None:
        """
        Specify the location of the Tahoe-LAFS web API.

        :param str nodeurl: A text string giving the URI root of the web API.
        """
        self.nodeurl = nodeurl

    async def _request(
        self, method: str, path: str = "", **kwargs: object
    ) -> str:
        if not self.nodeurl:
            raise RuntimeError(
                "Tahoe-LAFS nodeurl has not been set. Is tahoe running?"
            )
        if path.startswith("/") and self.nodeurl.endswith("/"):
            path = path.lstrip("/")
        url = self.nodeurl + path
        if "headers" not in kwargs:
            kwargs["headers"] = {"Accept": "text/plain"}
        resp = await treq.request(method, url, **kwargs)
        content = await treq.content(resp)
        decoded = content.decode("utf-8")
        if resp.code in (200, 201):
            return decoded
        raise TahoeWebError(
            f"Tahoe-LAFS web API responded with status code {resp.code}: "
            f"{decoded}"
        )

    async def get_grid_status(
        self,
    ) -> Optional[tuple[int, int, int]]:
        try:
            r = await self._request("GET", params={"t": "json"})
        except (ConnectError, RuntimeError, TahoeWebError):
            return None
        content = json.loads(r)
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

    async def is_ready(self) -> bool:
        if not self.shares_happy:
            return False
        status = await self.get_grid_status()
        if status is None:
            return False
        num_connected, _, _ = status
        return bool(num_connected and num_connected >= self.shares_happy)

    def await_ready(self) -> Deferred[bool]:
        return self._ready_poller.wait_for_completion()

    async def mkdir(
        self, parentcap: Optional[str] = None, childname: Optional[str] = None
    ) -> str:
        await self.await_ready()
        if parentcap and childname:
            path = f"/uri/{parentcap}"
            params = {"t": "mkdir", "name": childname}
        else:
            path = "/uri"
            params = {"t": "mkdir"}
        cap = await self._request("POST", path, params=params)
        return cap

    async def create_rootcap(self) -> str:
        return await self.rootcap_manager.create_rootcap()

    async def upload(
        self, local_path: str, dircap: str = "", mutable: bool = False
    ) -> str:
        if dircap:
            filename = Path(local_path).name
            path = f"/uri/{dircap}/{filename}"
        else:
            path = "/uri"
        if mutable:
            path = f"{path}?format=MDMF"
        log.debug("Uploading %s...", local_path)
        await self.await_ready()
        with open(local_path, "rb") as f:
            cap = await self._request("PUT", path, data=f)
        log.debug("Successfully uploaded %s", local_path)
        return cap

    async def download(self, cap: str, local_path: str) -> None:
        log.debug("Downloading %s...", local_path)
        await self.await_ready()
        resp = await treq.get(
            f"{self.nodeurl}uri/{cap}", headers={"Accept": "text/plain"}
        )
        if resp.code == 200:
            with atomic_write(local_path, mode="wb", overwrite=True) as f:
                # mypy: 'Argument 2 to "collect" of "treq" has
                # incompatible type overloaded function; expected
                # "Callable[[bytes], None]"'
                await treq.collect(resp, f.write)  # type: ignore
            log.debug("Successfully downloaded %s", local_path)
        else:
            content = await treq.content(resp)
            raise TahoeWebError(content.decode("utf-8"))

    async def link(self, dircap: str, childname: str, childcap: str) -> None:
        dircap_hash = trunchash(dircap)
        childcap_hash = trunchash(childcap)
        log.debug(
            'Linking "%s" (%s) into %s...',
            childname,
            childcap_hash,
            dircap_hash,
        )
        await self.await_ready()
        await self._request(
            "POST", f"/uri/{dircap}/?t=uri&name={childname}&uri={childcap}"
        )
        log.debug(
            'Done linking "%s" (%s) into %s',
            childname,
            childcap_hash,
            dircap_hash,
        )

    async def unlink(
        self, dircap: str, childname: str, missing_ok: bool = False
    ) -> None:
        dircap_hash = trunchash(dircap)
        log.debug('Unlinking "%s" from %s...', childname, dircap_hash)
        await self.await_ready()
        resp = await treq.post(
            f"{self.nodeurl}uri/{dircap}/?t=unlink&name={childname}",
            headers={"Accept": "text/plain"},
        )
        if resp.code == 404 and missing_ok:
            pass
        elif resp.code != 200:
            content = await treq.content(resp)
            raise TahoeWebError(content.decode("utf-8"))
        log.debug('Done unlinking "%s" from %s', childname, dircap_hash)

    async def get_json(self, cap: str) -> Optional[Union[dict, list]]:
        if not cap:
            return None
        try:
            content = await self._request("GET", f"/uri/{cap}/?t=json")
        except (ConnectError, RuntimeError, TahoeWebError):
            return None
        return json.loads(content)

    async def get_cap(self, path: str) -> Optional[str]:
        json_output = await self.get_json(path)
        if not json_output:
            return None
        data = json_output[1]
        return data.get("rw_uri", data.get("ro_uri", data.get("verify_uri")))

    async def ls(
        self,
        cap: str,
        exclude_dirnodes: bool = False,
        exclude_filenodes: bool = False,
    ) -> Optional[dict[str, dict]]:
        await self.await_ready()
        json_output = await self.get_json(cap)
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

    async def scan_storage_plugins(self) -> None:
        plugins = []
        log.debug("Scanning for known storage plugins...")
        try:
            version = await self.zkapauthorizer.get_version()
        except TahoeWebError:
            version = ""
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


def storage_options_to_config(options: dict) -> Optional[dict]:
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
