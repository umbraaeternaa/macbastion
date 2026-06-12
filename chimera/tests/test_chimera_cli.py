"""RED contract for the chimera CLI (SV-4). Fails against the NotImplementedError stubs;
green once parse_args / module_binary / launch_agent_plist land. Pure unit-level.
"""

import os
import sys
from pathlib import Path

from core.__main__ import (
    _bootout_argv,
    _bootstrap_argv,
    _chimera_root,
    _launch_agent_path,
    _module_python,
    _spawn_argv,
    launch_agent_plist,
    module_binary,
    parse_args,
)
from core.supervisor import ModuleSpec


def test_parse_args_none_is_bare_core():
    assert parse_args([]).command is None


# -- DP-1: spawn argv for native (binary) vs Python (-m) modules -------------


def test_spawn_argv_native_module(tmp_path):
    argv, env, cwd = _spawn_argv(ModuleSpec("echo"), tmp_path)
    assert argv == [str(module_binary("echo"))]
    assert env["CHIMERA_SOCKET_DIR"] == str(tmp_path)
    assert cwd == str(module_binary("echo").parent)  # run from its own dir (relative data)


def test_spawn_argv_python_module(tmp_path):
    argv, env, cwd = _spawn_argv(ModuleSpec("pulse", python=True), tmp_path)
    assert argv[0] == sys.executable
    assert argv[1:] == ["-m", "pulse"]
    assert env["CHIMERA_SOCKET_DIR"] == str(tmp_path)
    assert env["PYTHONPATH"] == str(module_binary("pulse").parent)
    assert cwd == str(module_binary("pulse").parent)


def test_parse_args_up():
    assert parse_args(["up"]).command == "up"


def test_parse_args_plist():
    assert parse_args(["plist"]).command == "plist"


def test_parse_args_shim_check():
    assert parse_args(["shim-check"]).command == "shim-check"


def test_parse_args_audit_defaults():
    args = parse_args(["audit"])
    assert args.command == "audit"
    assert args.n == 50
    assert args.failures is False  # show all by default


def test_parse_args_audit_failures_flag():
    # `chimera audit --failures` — mirror the core.audit failures-only filter locally.
    assert parse_args(["audit", "--failures"]).failures is True


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


def test_launch_agent_plist_sets_working_dir(tmp_path):
    # `python -m core up` only resolves `core` when cwd is the chimera dir (its parent).
    import core.__main__

    chimera_dir = Path(core.__main__.__file__).resolve().parent.parent
    xml = launch_agent_plist(tmp_path)
    assert "<key>WorkingDirectory</key>" in xml
    assert str(chimera_dir) in xml


# -- SV-5: install / uninstall (one-command persistence) ---------------------


def test_parse_args_install():
    assert parse_args(["install"]).command == "install"


def test_parse_args_uninstall():
    assert parse_args(["uninstall"]).command == "uninstall"


def test_launch_agent_path_is_user_launchagents():
    # The plist goes to the per-user LaunchAgents dir under the canonical label.
    p = _launch_agent_path()
    assert p == Path.home() / "Library/LaunchAgents/com.umbra.chimera.plist"
    assert p.name == "com.umbra.chimera.plist"


def test_bootstrap_argv_targets_gui_domain():
    # `launchctl bootstrap gui/<uid> <plist>` loads the agent into the user's GUI domain.
    plist = Path("/x/com.umbra.chimera.plist")
    assert _bootstrap_argv(plist) == [
        "launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist)
    ]


def test_bootout_argv_targets_gui_domain():
    # `launchctl bootout gui/<uid> <plist>` unloads the agent from the user's GUI domain.
    plist = Path("/x/com.umbra.chimera.plist")
    assert _bootout_argv(plist) == [
        "launchctl", "bootout", f"gui/{os.getuid()}", str(plist)
    ]


# -- TE-frozen: frozen-aware module + interpreter resolution (the signed core runs the organism) --


def test_chimera_root_unfrozen_is_project_dir():
    # Unfrozen: the chimera dir holding modules/ — this is where module_binary resolves from.
    root = _chimera_root()
    assert (root / "modules").is_dir()
    assert root == module_binary("echo").parent.parent.parent  # <root>/modules/echo/echo


def test_chimera_root_env_override(monkeypatch):
    monkeypatch.setenv("CHIMERA_ROOT", "/opt/chimera")
    assert _chimera_root() == Path("/opt/chimera")


def test_module_python_unfrozen_is_sys_executable(monkeypatch):
    # Unfrozen, no override: the venv python (sys.executable) already runs `-m oracle`.
    monkeypatch.delenv("CHIMERA_PYTHON", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert _module_python() == sys.executable


def test_module_python_env_override(monkeypatch):
    # The override wins — used to point the frozen core at a real interpreter for oracle/pulse.
    monkeypatch.setenv("CHIMERA_PYTHON", "/usr/bin/python3")
    assert _module_python() == "/usr/bin/python3"
