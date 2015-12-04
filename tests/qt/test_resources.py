# -*- coding: utf-8 -*-

import pytest

from gridsync.resources import (qt_resource_data, qt_resource_name,
        qt_resource_struct, qInitResources, qCleanupResources)


def test_qt_resource_data():
    assert qt_resource_data

def test_qt_resource_name():
    assert qt_resource_name

def test_qt_resource_struct():
    assert qt_resource_struct

def test_qInitResources():
    assert qInitResources() == None

def test_qCleanupResources():
    assert qCleanupResources() == None
