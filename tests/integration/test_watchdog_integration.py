import os
import sys

import pytest

from gridsync.watchdog import Watchdog


@pytest.fixture(scope="module")
def watchdog():
    wd = Watchdog()
    wd.start()
    yield wd
    wd.stop()


@pytest.mark.skipif(
    "CI" in os.environ, reason="Flakey on public infrastructure"
)
def test_watchdog_emits_path_modified_signal(watchdog, tmp_path, qtbot):
    watchdog.add_watch(str(tmp_path))
    with qtbot.wait_signal(watchdog.path_modified) as blocker:
        file_path = tmp_path / "File.txt"
        file_path.write_text("")
    assert blocker.args == [str(tmp_path)]
