# -*- coding: utf-8 -*-

import base64
import logging as log
import os
import shutil
import sys
from binascii import Error
from typing import Optional, cast
from urllib.parse import urlparse

import treq
from atomicwrites import atomic_write
from qtpy.QtCore import QObject, Qt, Signal
from qtpy.QtWidgets import QInputDialog, QLineEdit, QMessageBox, QWidget
from twisted.internet import reactor as reactor_module
from twisted.internet.defer import Deferred
from twisted.internet.interfaces import IReactorCore

from gridsync import APP_NAME, config_dir, resource
from gridsync.config import Config
from gridsync.errors import (
    AbortedByUserError,
    RestorationError,
    TorError,
    UpgradeRequiredError,
)
from gridsync.msg import error
from gridsync.tahoe import Tahoe
from gridsync.tor import get_tor, get_tor_with_prompt, tor_required
from gridsync.zkapauthorizer import PLUGIN_NAME as ZKAPAUTHZ_PLUGIN_NAME

# mypy thinks reactor is a module
# https://github.com/twisted/twisted/issues/9909
reactor = cast(IReactorCore, reactor_module)


def is_onion_grid(settings: dict) -> bool:
    furls = []
    introducer = settings.get("introducer")
    if introducer:
        furls.append(introducer)
    servers = settings.get("storage")
    if servers:
        for data in servers.values():
            if "anonymous-storage-FURL" in data:
                furls.append(data.get("anonymous-storage-FURL"))
    for furl in furls:
        if tor_required(furl):
            return True
    return False


def is_zkap_grid(settings: dict) -> tuple[bool, set]:
    hosts = set()
    url = settings.get("zkap_payment_url_root")
    if url:
        hosts.add(urlparse(url).hostname)
    zkapauthz = False
    storage_servers = settings.get("storage")
    if storage_servers:
        for data in storage_servers.values():
            storage_options = data.get("storage-options")
            if not storage_options:
                continue
            for group in storage_options:
                if group.get("name") == ZKAPAUTHZ_PLUGIN_NAME:
                    zkapauthz = True
                url = group.get("ristretto-issuer-root-url")
                if url:
                    hosts.add(urlparse(url).hostname)
    if zkapauthz or hosts:
        return (True, hosts)
    return (False, hosts)


def prompt_for_leaky_tor(
    grid_name: str, hosts: set, parent: Optional[QWidget] = None
) -> bool:
    msgbox = QMessageBox(parent)
    msgbox.setWindowModality(Qt.ApplicationModal)
    msgbox.setIcon(QMessageBox.Warning)
    title = "WARNING: Possible anonymity-leak ahead!"
    hosts_list = ""
    for host in hosts:
        hosts_list += (  # pylint: disable=consider-using-join
            f"<p><b>{host}</b>"
        )
    text = (
        f"The <i>{grid_name}</i> grid requires the use of Zero-Knowledge "
        "Access Passes (ZKAPs), however, the Tahoe-LAFS ZKAPAuthorizer "
        "plugin that is used to redeem ZKAPs does not currently support "
        "tunneling its connections over Tor.<p>"
        "With Tor enabled, your local IP address will continue to be "
        f"concealed from the storage servers that comprise the {grid_name} "
        "grid, however, without taking any further precautions, the act of "
        "purchasing or reedeming ZKAPs will expose your IP address to the "
        f"following hosts, at minimum:{hosts_list}<p>"
    )
    if sys.platform == "darwin":
        msgbox.setText(title)
        msgbox.setInformativeText(text)
    else:
        msgbox.setWindowTitle(title)
        msgbox.setText(text)
    ok = msgbox.addButton("Continue with Tor enabled", QMessageBox.AcceptRole)
    msgbox.addButton(QMessageBox.Abort)
    msgbox.exec_()
    if msgbox.clickedButton() == ok:
        return True
    return False


def prompt_for_grid_name(
    grid_name: str, parent: Optional[QWidget] = None
) -> tuple[str, int]:
    title = "{} - Choose a name".format(APP_NAME)
    label = "Please choose a name for this connection:"
    if grid_name:
        label = (
            '{} is already connected to "{}".\n\n'
            "Please choose a different name for this connection".format(
                APP_NAME, grid_name
            )
        )
    return QInputDialog.getText(
        # According to the Qt5 docs, QInputDialog accepts a null parent:
        # https://doc.qt.io/qt-5/qinputdialog.html#QInputDialog
        parent,  # type: ignore
        title,
        label,
        QLineEdit.Normal,
        grid_name,
    )


def validate_grid(settings: dict, parent: Optional[QWidget] = None) -> dict:
    nickname = settings.get("nickname", "")
    while not nickname:
        nickname, _ = prompt_for_grid_name(nickname, parent)
    nodedir = os.path.join(config_dir, nickname)
    if os.path.isdir(nodedir):
        conflicting_introducer = False
        introducer = settings.get("introducer")
        if introducer:
            config = Config(os.path.join(nodedir, "tahoe.cfg"))
            existing_introducer = config.get("client", "introducer.furl")
            if introducer != existing_introducer:
                conflicting_introducer = True

        conflicting_servers = False
        servers = settings.get("storage")
        if servers:
            existing_servers = Tahoe(nodedir).get_storage_servers()
            if servers != existing_servers:
                conflicting_servers = True

        if conflicting_introducer or conflicting_servers:
            while os.path.isdir(os.path.join(config_dir, nickname)):
                nickname, _ = prompt_for_grid_name(nickname, parent)
    settings["nickname"] = nickname
    return settings


def prompt_for_folder_name(
    folder_name: str, grid_name: str, parent: Optional[QWidget] = None
) -> tuple[str, int]:
    return QInputDialog.getText(
        # According to the Qt5 docs, QInputDialog accepts a null parent:
        # https://doc.qt.io/qt-5/qinputdialog.html#QInputDialog
        parent,  # type: ignore
        "Folder already exists",
        'You already belong to a folder named "{}" on\n'
        "{}; Please choose a different name.".format(folder_name, grid_name),
        QLineEdit.Normal,
        folder_name,
    )


def validate_folders(
    settings: dict, known_gateways: list, parent: Optional[QWidget] = None
) -> dict:
    gateway = None
    if known_gateways:
        for gw in known_gateways:
            if gw.name == settings["nickname"]:
                gateway = gw
    if not gateway:
        return settings
    for folder, data in settings["magic-folders"].copy().items():
        target = folder
        while gateway.magic_folder.folder_exists(target):
            target, ok = prompt_for_folder_name(target, gateway.name, parent)
            if not ok:  # User clicked "Cancel"; skip this folder
                del settings["magic-folders"][folder]
                continue
            if not target:
                target = folder
            elif (
                not gateway.magic_folder.folder_exists(target)
                and target not in settings["magic-folders"]
            ):
                settings["magic-folders"][target] = data
                del settings["magic-folders"][folder]
    return settings


def validate_settings(
    settings: dict,
    known_gateways: list,
    parent: Optional[QWidget] = None,
    from_wormhole: bool = True,
) -> dict:
    if from_wormhole and "rootcap" in settings:
        del settings["rootcap"]
    if from_wormhole and "convergence" in settings:
        del settings["convergence"]
    settings = validate_grid(settings, parent)
    if "magic-folders" in settings:
        settings = validate_folders(settings, known_gateways, parent)
    return settings


class SetupRunner(QObject):
    grid_already_joined = Signal(str)
    update_progress = Signal(str)
    client_started = Signal(object)
    joined_folders = Signal(list)
    got_icon = Signal(str)
    done = Signal(object)

    def __init__(self, known_gateways: list, use_tor: bool = False) -> None:
        super().__init__()
        self.known_gateways = known_gateways
        self.use_tor = use_tor
        self.gateway = Tahoe()

    def get_gateway(self, introducer: str, servers: dict) -> Optional[Tahoe]:
        if not self.known_gateways:
            return None
        for gateway in self.known_gateways:
            target_introducer = gateway.config_get("client", "introducer.furl")
            if introducer and introducer == target_introducer:
                return gateway
            target_servers = gateway.get_storage_servers()
            if servers and servers == target_servers:
                return gateway
        return None

    def calculate_total_steps(self, settings: dict) -> int:
        steps = 1  # done
        if not self.get_gateway(
            settings.get("introducer", ""), settings.get("storage", {})
        ):
            steps += 4  # create, start, await_ready, rootcap
        if (
            "zkap_unit_name" in settings
            or "zkap_unit_multiplier" in settings
            or "zkap_payment_url_root" in settings
        ):
            # "starting", "downloading", "verifying", "success"
            steps += 4
        folders = settings.get("magic-folders")
        if folders:
            steps += len(folders)  # join
        return steps

    def decode_icon(self, s: str, dest: str) -> None:
        with atomic_write(dest, mode="wb", overwrite=True) as f:
            try:
                f.write(base64.b64decode(s))
            except (Error, TypeError):
                return
        self.got_icon.emit(dest)

    async def fetch_icon(self, url: str, dest: str) -> None:
        agent = None
        if self.use_tor:
            tor = await get_tor(reactor)
            if not tor:
                raise TorError("Could not connect to a running Tor daemon")
            agent = tor.web_agent()
        resp = await treq.get(url, agent=agent)
        if resp.code == 200:
            content = await treq.content(resp)
            log.debug("Received %i bytes", len(content))
            with atomic_write(dest, mode="wb", overwrite=True) as f:
                f.write(content)
            self.got_icon.emit(dest)
        else:
            log.warning("Error fetching service icon: %i", resp.code)

    async def join_grid(  # noqa: max-complexity=14 XXX
        self, settings: dict
    ) -> None:
        nickname = settings["nickname"]
        if self.use_tor:
            msg = "Connecting to {} via Tor...".format(nickname)
        else:
            msg = "Connecting to {}...".format(nickname)
        self.update_progress.emit(msg)

        icon_path = None
        if nickname in ("Least Authority S4", "HRO Cloud"):
            icon_path = resource("leastauthority.com.icon")
            self.got_icon.emit(icon_path)
        elif "icon_base64" in settings:
            icon_path = os.path.join(config_dir, ".icon.tmp")
            self.decode_icon(settings["icon_base64"], icon_path)
        elif "icon_url" in settings:
            # A temporary(?) measure to get around the performance issues
            # observed when transferring a base64-encoded icon through Least
            # Authority's wormhole server. Hopefully this will go away.. See:
            # https://github.com/LeastAuthority/leastauthority.com/issues/539
            log.debug("Fetching service icon from %s...", settings["icon_url"])
            icon_path = os.path.join(config_dir, ".icon.tmp")
            try:
                # It's probably not worth cancelling or holding-up the setup
                # process if fetching/writing the icon fails (particularly
                # if doing so would require the user to get a new invite code)
                # so just log a warning for now if something goes wrong...
                await self.fetch_icon(settings["icon_url"], icon_path)
            except Exception as e:  # pylint: disable=broad-except
                log.warning("Error fetching service icon: %s", str(e))

        nodedir = os.path.join(config_dir, nickname)
        self.gateway = Tahoe(nodedir)
        await Deferred.fromCoroutine(self.gateway.create_client(settings))

        self.gateway.save_settings(settings)

        if icon_path:
            try:
                shutil.copy(icon_path, os.path.join(nodedir, "icon"))
            except OSError as err:
                log.warning("Error copying icon file: %s", str(err))
        if "icon_url" in settings:
            try:
                with atomic_write(
                    os.path.join(nodedir, "icon.url"), mode="w", overwrite=True
                ) as f:
                    f.write(settings["icon_url"])
            except OSError as err:
                log.warning("Error writing icon url to file: %s", str(err))

        self.update_progress.emit(msg)
        await self.gateway.start()
        self.client_started.emit(self.gateway)
        self.update_progress.emit(msg)
        await self.gateway.await_ready()

    async def _restore_zkaps(self, recovery_cap: str) -> None:
        def status_updated(stage: str, failure_reason: str) -> None:
            # From https://github.com/PrivateStorageio/ZKAPAuthorizer/
            # blob/129fdf1c1a73089da796032f06320fe17f69d711/src/
            # _zkapauthorizer/recover.py#L35
            stages = {
                "started": "ZKAPs recovery started",
                "inspect_replica": "Inspecting ZKAPs replica",
                "downloading": "Downloading ZKAPs",
                "importing": "Importing ZKAPs",
                "succeeded": "Finalizing restoration",
            }
            if failure_reason is None:
                humanized_stage = stages.get(stage, stage.title())
                self.update_progress.emit(humanized_stage + "...")
            else:
                self.update_progress.emit(f"Recovery failed: {failure_reason}")
                error(None, "Error restoring ZKAPs", str(failure_reason))

        log.debug("Restoring ZKAPs from backup...")
        await self.gateway.zkapauthorizer.restore_zkaps(
            status_updated, recovery_cap=recovery_cap
        )

    async def ensure_recovery(self, settings: dict) -> None:
        zkapauthz, _ = is_zkap_grid(settings)
        rootcap = settings.get("rootcap")
        if rootcap:
            self.update_progress.emit("Restoring from Recovery Key...")
            if zkapauthz:
                help_text = (
                    "\n\nThis may indicate that your Recovery Key was created "
                    f"with a version of {APP_NAME} that is incompatible with "
                    "the current version of the software or that the data is "
                    f'no longer available on "{self.gateway.name}".\n\nPlease '
                    "contact your storage provider for further assistance."
                )
                za = self.gateway.zkapauthorizer
                recovery_cap = await za.get_recovery_capability(rootcap)
                if recovery_cap is None:
                    raise RestorationError(
                        "Cannot restore from Recovery Key; no ZKAPs "
                        f"recovery-capability found in rootcap.{help_text}"
                    )
                snapshot_exists = await za.snapshot_exists(recovery_cap)
                if not snapshot_exists:
                    # `_restore_zkaps` will hang forever if no snapshot exists
                    raise RestorationError(
                        "Cannot restore from Recovery Key; no ZKAPs "
                        f"snapshot(s) found in recovery-capability.{help_text}"
                    )
                await self._restore_zkaps(recovery_cap)
            await self.gateway.rootcap_manager.import_rootcap(rootcap)
            if zkapauthz:
                # This must happen *after* the `import_rootcap` call
                # above, since both `import_rootcap` and `backup_zkaps`
                # will overwrite the contents of the ".zkapauthorizer"
                # backup directory inside the new rootcap (and we don't
                # want the new backup -- from `backup_zkaps` -- to be
                # overwritten by the old one -- from `import_rootcap`).
                await self.gateway.zkapauthorizer.backup_zkaps()
            # Force MagicFolderMonitor to detect newly-restored folders
            await self.gateway.magic_folder.monitor.do_check()  # XXX
        elif zkapauthz:
            self.update_progress.emit("Connecting...")
        else:
            self.update_progress.emit("Creating Recovery Key...")
            await self.gateway.create_rootcap()

    async def join_folders(self, folders_data: dict) -> None:
        folders = []
        for folder, data in folders_data.items():
            self.update_progress.emit('Joining folder "{}"...'.format(folder))
            collective, personal = data["code"].split("+")
            await self.gateway.link(
                self.gateway.get_rootcap(),
                folder + " (collective)",
                collective,
            )
            await self.gateway.link(
                self.gateway.get_rootcap(), folder + " (personal)", personal
            )
            folders.append(folder)
        if folders:
            self.joined_folders.emit(folders)

    async def run(self, settings: dict) -> None:
        if "version" in settings and int(settings["version"]) > 2:
            raise UpgradeRequiredError

        nickname = settings.get("nickname", "")

        if self.use_tor or "hide-ip" in settings or is_onion_grid(settings):
            settings["hide-ip"] = True
            self.use_tor = True
            tor = await get_tor_with_prompt(reactor)
            if not tor:
                raise TorError("Could not connect to a running Tor daemon")

            zkap_grid, hosts = is_zkap_grid(settings)
            if zkap_grid:
                permission_granted = prompt_for_leaky_tor(nickname, hosts)
                if not permission_granted:
                    raise AbortedByUserError("The user aborted the operation")

        gateway = self.get_gateway(
            settings.get("introducer", ""), settings.get("storage", {})
        )
        if gateway:
            self.gateway = gateway
        folders_data = settings.get("magic-folders")
        if not gateway:
            await self.join_grid(settings)
            await self.ensure_recovery(settings)
        elif not folders_data:
            self.grid_already_joined.emit(nickname)
        if folders_data:
            await self.join_folders(folders_data)

        self.update_progress.emit("Done!")
        self.done.emit(self.gateway)
