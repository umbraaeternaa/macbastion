"""RED contract for the chimera CLI (SV-4). Fails against the NotImplementedError stubs;
green once parse_args / module_binary / launch_agent_plist land. Pure unit-level.
"""

from pathlib import Path

from core.__main__ import launch_agent_plist, module_binary, parse_args


def test_parse_args_none_is_bare_core():
    assert parse_args([]).command is None


def test_parse_args_up():
    assert parse_args(["up"]).command == "up"


def test_parse_args_plist():
    assert parse_args(["plist"]).command == "plist"


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
