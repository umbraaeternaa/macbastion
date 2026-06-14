"""EP-9 (ECHO_PACKET §7): the echo-shaper installer's pf.conf hook management.

The installer's only risky logic is editing the system /etc/pf.conf to add the required
`dummynet-anchor "com.chimera.echo"` attachment point (F1). We test that logic ROOT-FREE by
pointing the script's `PF_CONF` env at a tmp copy of a stock pf.conf — the `--add-hook` /
`--remove-hook` subcommands operate on $PF_CONF only and run no pfctl/launchctl. The real
`pfctl -f` reload + binary/plist/bootstrap belong to the full (root) install path, not here.
"""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "deploy" / "install-echo-shaper.sh"

HOOK_LINE = 'dummynet-anchor "com.chimera.echo"'

# A stock macOS /etc/pf.conf — only the com.apple anchor point.
STOCK_PF = """\
scrub-anchor "com.apple/*"
nat-anchor "com.apple/*"
rdr-anchor "com.apple/*"
dummynet-anchor "com.apple/*"
anchor "com.apple/*"
load anchor "com.apple" from "/etc/pf.anchors/com.apple"
"""

APPLE_LINES = [
    'scrub-anchor "com.apple/*"',
    'dummynet-anchor "com.apple/*"',
    'anchor "com.apple/*"',
    'load anchor "com.apple" from "/etc/pf.anchors/com.apple"',
]


def _run(subcmd: str, pf_conf: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "PF_CONF": str(pf_conf)}
    return subprocess.run(
        ["bash", str(SCRIPT), subcmd],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


@pytest.fixture()
def pf_conf(tmp_path: Path) -> Path:
    p = tmp_path / "pf.conf"
    p.write_text(STOCK_PF)
    return p


def test_add_hook_inserts_line_and_backs_up(pf_conf: Path) -> None:
    res = _run("--add-hook", pf_conf)
    assert res.returncode == 0, res.stderr
    text = pf_conf.read_text()
    assert HOOK_LINE in text  # our attachment point is present
    for line in APPLE_LINES:  # stock com.apple ruleset untouched
        assert line in text
    backup = Path(str(pf_conf) + ".chimera-bak")
    assert backup.exists()  # a pre-edit backup was written
    assert HOOK_LINE not in backup.read_text()  # backup is the original (no hook)


def test_add_hook_is_idempotent(pf_conf: Path) -> None:
    _run("--add-hook", pf_conf)
    _run("--add-hook", pf_conf)  # second run must not duplicate
    text = pf_conf.read_text()
    assert text.count(HOOK_LINE) == 1


def test_remove_hook_restores_stock(pf_conf: Path) -> None:
    _run("--add-hook", pf_conf)
    res = _run("--remove-hook", pf_conf)
    assert res.returncode == 0, res.stderr
    text = pf_conf.read_text()
    assert HOOK_LINE not in text  # our line is gone
    for line in APPLE_LINES:  # stock ruleset still intact
        assert line in text
