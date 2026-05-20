"""Port scanner module — finds all listening TCP/UDP sockets on the system."""

import subprocess
from dataclasses import dataclass
from typing import Literal

Exposure = Literal["localhost", "all_interfaces", "specific"]


@dataclass
class ListeningPort:
    """Represents a single listening network socket."""

    command: str  # process name (e.g., "launchd", "node")
    pid: int  # process ID
    user: str  # user that owns the process
    protocol: str  # "TCP" or "UDP"
    address: str  # bind address (e.g., "127.0.0.1", "*", "[::1]")
    port: int  # port number
    exposure: Exposure  # localhost / all_interfaces / specific


def _classify_exposure(address: str) -> Exposure:
    """Determine how exposed a listening socket is."""
    if address in ("*", "0.0.0.0", "::"):
        return "all_interfaces"
    if address in ("127.0.0.1", "[::1]") or address.startswith("127."):
        return "localhost"
    return "specific"


def _parse_lsof_line(line: str) -> ListeningPort | None:
    """Parse a single line of `lsof -iTCP -sTCP:LISTEN -nP` output."""
    # Expected columns: COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME
    parts = line.split()
    if len(parts) < 9:
        return None

    command = parts[0]
    try:
        pid = int(parts[1])
    except ValueError:
        return None
    user = parts[2]
    protocol = parts[7]  # "TCP" or "UDP"
    name = parts[8]  # e.g., "*:3031" or "127.0.0.1:8021"

    # Split "address:port" — handle IPv6 brackets
    if name.endswith("(LISTEN)"):
        name = name.rsplit("(", 1)[0].strip()

    if ":" not in name:
        return None

    address, _, port_str = name.rpartition(":")
    try:
        port = int(port_str)
    except ValueError:
        return None

    return ListeningPort(
        command=command,
        pid=pid,
        user=user,
        protocol=protocol,
        address=address,
        port=port,
        exposure=_classify_exposure(address),
    )


def scan_listening_ports() -> list[ListeningPort]:
    """Run lsof and return all listening TCP sockets."""
    try:
        result = subprocess.run(
            ["sudo", "lsof", "-iTCP", "-sTCP:LISTEN", "-nP"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"lsof failed: {e.stderr}") from e

    lines = result.stdout.strip().splitlines()
    # Skip header line
    if lines and lines[0].startswith("COMMAND"):
        lines = lines[1:]

    ports: list[ListeningPort] = []
    for line in lines:
        parsed = _parse_lsof_line(line)
        if parsed:
            ports.append(parsed)
    return ports
