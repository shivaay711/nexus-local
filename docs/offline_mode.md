# Offline Modes and the Network Guard

## Modes
- **Air-Gapped** (`NEXUS_OFFLINE_MODE=air_gapped`, default): Network Guard is
  enabled at app startup; all non-loopback sockets and DNS lookups raise
  `NetworkBlockedError` and are logged as SecurityEvents.
- **Offline-Ready** (`offline_ready`): for one-time setup (pip installs,
  `ollama pull`). Normal operation should return to Air-Gapped.

## What the guard blocks (verified by tests + a live httpx call)
- `socket.socket.connect` / `connect_ex` to non-loopback hosts
- `socket.getaddrinfo` DNS resolution for non-loopback hosts
- Therefore: all httpx/requests/urllib traffic from application code,
  including any remote LLM/embedding/telemetry endpoint

## What it cannot block (documented, not hidden)
Application-level blocking cannot replace OS firewall rules. It does not
constrain child processes or native libraries with their own sockets.

## Hard enforcement on Windows 11 (recommended additional layer)
```powershell
# Block all outbound traffic for the NEXUS python process except loopback
New-NetFirewallRule -DisplayName "NEXUS Local block outbound" `
  -Direction Outbound -Program "C:\path\to\venv\Scripts\python.exe" `
  -Action Block -Profile Any
# Loopback traffic is not filtered by Windows Firewall, so local Ollama still works.
```
For Docker: run with `--network none`, or an internal-only compose network.
