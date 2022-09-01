# -*- coding: utf-8 -*-


class GridsyncError(Exception):
    pass


class AbortedByUserError(GridsyncError):
    pass


class FilesystemLockError(GridsyncError):
    pass


class UpgradeRequiredError(GridsyncError):
    pass


class TahoeError(GridsyncError):
    pass


class TahoeCommandError(TahoeError):
    pass


class TahoeWebError(TahoeError):
    pass


class TorError(GridsyncError):
    pass


class RestorationError(GridsyncError):
    pass
