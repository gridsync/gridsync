# -*- coding: utf-8 -*-


class GridsyncError(Exception):
    pass


class NodedirExistsError(GridsyncError):
    pass


class UpgradeRequiredError(GridsyncError):
    pass
