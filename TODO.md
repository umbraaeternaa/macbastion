# TODO

## v0.2 — Polish port scanner
- [ ] Deduplicate IPv4+IPv6 rows (same PID + port)
- [ ] Add --json flag for machine-readable output
- [ ] Add tests in tests/test_ports.py
- [ ] Improve README with example output

## v0.3 — Second scanner
- [ ] LaunchAgents / LaunchDaemons analyzer
- [ ] Detect Apple-spoofing (e.g., com.apple.* outside /System)
- [ ] Code signature verification

## v0.4 — TCC scanner
- [ ] Read TCC.db
- [ ] Find orphan permissions (from uninstalled apps)
