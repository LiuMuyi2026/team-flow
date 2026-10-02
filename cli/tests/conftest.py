import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from tf_stub_server import Stub  # noqa: E402
from tfhelpers import Env  # noqa: E402


@pytest.fixture
def stub():
    s = Stub().start()
    yield s
    s.stop()


@pytest.fixture
def env(tmp_path, monkeypatch):
    e = Env(tmp_path)
    for k, v in e.vars.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("HOME", e.home)
    return e
