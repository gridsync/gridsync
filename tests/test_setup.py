# -*- coding: utf-8 -*-

from gridsync.setup import prompt_for_grid_name, prompt_for_folder_name


def test_prompt_for_grid_name(monkeypatch):
    monkeypatch.setattr(
        'gridsync.setup.QInputDialog.getText',
        lambda a, b, c, d, e: ('NewGridName', 1)
    )
    assert prompt_for_grid_name('GridName', 1) == ('NewGridName', 1)


def test_prompt_for_folder_name(monkeypatch):
    monkeypatch.setattr(
        'gridsync.setup.QInputDialog.getText',
        lambda a, b, c, d, e: ('NewFolderName', 1)
    )
    assert prompt_for_folder_name('FolderName', "", 1) == ('NewFolderName', 1)
