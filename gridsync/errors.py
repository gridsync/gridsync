# -*- coding: utf-8 -*-


class GridsyncError(Exception):
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
