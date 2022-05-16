import pytest

from gridsync.crypto import randstr
from gridsync.system import which


def test_which():
    path = which("python")
    assert "python" in path


def test_which_raises_environment_error():
    with pytest.raises(EnvironmentError):
        which(randstr(32))
