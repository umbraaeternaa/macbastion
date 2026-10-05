"""Test-session temp-path shortening for macOS AF_UNIX limits.

macOS caps a UNIX-socket path at 104 bytes. The system temp dir on this
machine (`/var/folders/.../T`) is long enough that pytest's numbered
`tmp_path` + `core.sock` overflows it, so every real-socket test dies with
``OSError: AF_UNIX path too long`` before touching any product code.

This conftest pins the test session (and any subprocess it spawns) to the
short `/tmp` root so socket paths stay well under the limit. It affects
ONLY the test run — product defaults (`~/.config/chimera/run`) are
untouched. POSIX-only; on other platforms it is a no-op.
"""

from __future__ import annotations

import os
import tempfile

_SHORT_TMP = "/tmp"
"""Short POSIX temp root — `/tmp/<pytest-N>/<test>/core.sock` fits 104 bytes."""


def _install_short_tmp() -> None:
    """Point this process (and inherited subprocesses) at the short temp root."""
    if os.name != "posix":
        return
    os.environ["TMPDIR"] = _SHORT_TMP
    tempfile.tempdir = _SHORT_TMP


# Import time: run before the first `tmp_path` is materialised.
_install_short_tmp()


def pytest_configure() -> None:
    # Belt and braces: re-assert after plugin configuration, in case a plugin
    # already cached the long system temp dir before this file was imported.
    _install_short_tmp()
