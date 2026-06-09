"""RED contract for the chimera CLI (SV-4). Fails against the NotImplementedError stubs;
green once parse_args / module_binary / launch_agent_plist land. Pure unit-level.
"""

import sys
from pathlib import Path

from core.__main__ import launch_agent_plist, module_binary, parse_args


def test_parse_args_none_is_bare_core():
    assert parse_args([]).command is None


def test_parse_args_up():
    assert parse_args(["up"]).command == "up"


def test_parse_args_plist():
    assert parse_args(["plist"]).command == "plist"


def test_parse_args_shim_check():
    assert parse_args(["shim-check"]).command == "shim-check"


def test_module_binary_path():
    p = module_binary("echo")
    assert isinstance(p, Path)
    assert p.name == "echo"
    assert p.parent.name == "echo"
    assert "modules" in p.parts


def test_launch_agent_plist_has_keys(tmp_path):
    xml = launch_agent_plist(tmp_path)
    assert "ProgramArguments" in xml
    assert "Label" in xml
    assert str(tmp_path) in xml
    assert "up" in xml  # the agent runs `python -m core up`


def test_launch_agent_plist_frozen_uses_bare_up(tmp_path, monkeypatch):
    # A signed frozen binary IS the entry point -> `chimera up`, not `chimera -m core up`.
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/opt/chimera/chimera")
    xml = launch_agent_plist(tmp_path)
    assert "<string>-m</string>" not in xml
    assert "<string>core</string>" not in xml
    assert "<string>/opt/chimera/chimera</string>" in xml
    assert "<string>up</string>" in xml


def test_launch_agent_plist_unfrozen_uses_dash_m_core(tmp_path, monkeypatch):
    # Dev mode (python -m core): the interpreter needs `-m core up`.
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    xml = launch_agent_plist(tmp_path)
    assert "<string>-m</string>" in xml
    assert "<string>core</string>" in xml
