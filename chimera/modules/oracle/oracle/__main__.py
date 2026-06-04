"""Daemon entry — `python -m oracle` (§5.3).

Wires CoreConfig (socket_dir from CHIMERA_SOCKET_DIR), the BaselineStore, and
the dual-role OracleClient, then runs the asyncio loop until a signal arrives.

STUB — RED slice. Not exercised by tests this slice (integration runs the
client in-process). Standalone-run path resolution (`python -m oracle` needs
modules/oracle on sys.path) is a GREEN concern.
"""


def main() -> None:
    """Run the ORACLE daemon."""
    raise NotImplementedError("oracle daemon entry — RED slice")


if __name__ == "__main__":
    main()
