"""Network Guard.

Application-level enforcement that no NEXUS service opens an outbound network
connection. It patches ``socket.socket.connect`` (and ``connect_ex``) in this
process and rejects any destination that is not loopback (or, in
OFFLINE_READY mode, not on the explicit allowlist).

Every blocked attempt is recorded in memory and, when a DB session factory is
available, as a SecurityEvent row.

HONEST LIMITATION (also documented in docs/offline_mode.md): a process-level
guard cannot constrain child processes or native libraries that bypass Python
sockets. For hard guarantees, pair this with OS firewall rules; the user guide
shows the Windows Firewall commands.
"""
from __future__ import annotations

import datetime as dt
import socket
import threading
from dataclasses import dataclass, field


class NetworkBlockedError(ConnectionError):
    pass


_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


@dataclass
class NetworkGuard:
    enabled: bool = False
    allowlist: set[str] = field(default_factory=set)  # extra hosts in offline_ready setup
    blocked_attempts: list[dict] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _orig_connect: object = field(default=None, repr=False)
    _orig_connect_ex: object = field(default=None, repr=False)
    _orig_getaddrinfo: object = field(default=None, repr=False)

    def _host_of(self, address) -> str:
        if isinstance(address, tuple) and address:
            return str(address[0])
        return str(address)

    def _permitted(self, host: str) -> bool:
        return host in _LOOPBACK or host.startswith("127.") or host in self.allowlist

    def _record(self, host: str, via: str) -> None:
        entry = {
            "host": host,
            "via": via,
            "at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        with self._lock:
            self.blocked_attempts.append(entry)
        try:  # best-effort persistence; guard must work before DB exists
            from ..db import get_session
            from ..models import SecurityEvent
            with get_session() as s:
                s.add(SecurityEvent(kind="network_blocked", detail=f"{via} -> {host}"))
                s.commit()
        except Exception:
            pass

    def enable(self) -> None:
        if self.enabled:
            return
        self._orig_connect = socket.socket.connect
        self._orig_connect_ex = socket.socket.connect_ex
        self._orig_getaddrinfo = socket.getaddrinfo
        guard = self

        def guarded_connect(sock, address):
            host = guard._host_of(address)
            if not guard._permitted(host):
                guard._record(host, "socket.connect")
                raise NetworkBlockedError(f"Network Guard blocked outbound connection to {host}")
            return guard._orig_connect(sock, address)  # type: ignore[operator]

        def guarded_connect_ex(sock, address):
            host = guard._host_of(address)
            if not guard._permitted(host):
                guard._record(host, "socket.connect_ex")
                raise NetworkBlockedError(f"Network Guard blocked outbound connection to {host}")
            return guard._orig_connect_ex(sock, address)  # type: ignore[operator]

        def guarded_getaddrinfo(host, *args, **kwargs):
            h = str(host)
            if not guard._permitted(h):
                guard._record(h, "dns.getaddrinfo")
                raise NetworkBlockedError(f"Network Guard blocked DNS lookup for {h}")
            return guard._orig_getaddrinfo(host, *args, **kwargs)  # type: ignore[operator]

        socket.socket.connect = guarded_connect  # type: ignore[assignment]
        socket.socket.connect_ex = guarded_connect_ex  # type: ignore[assignment]
        socket.getaddrinfo = guarded_getaddrinfo  # type: ignore[assignment]
        self.enabled = True

    def disable(self) -> None:
        if not self.enabled:
            return
        socket.socket.connect = self._orig_connect  # type: ignore[assignment]
        socket.socket.connect_ex = self._orig_connect_ex  # type: ignore[assignment]
        socket.getaddrinfo = self._orig_getaddrinfo  # type: ignore[assignment]
        self.enabled = False

    def status(self) -> dict:
        with self._lock:
            last = self.blocked_attempts[-1] if self.blocked_attempts else None
            return {
                "enabled": self.enabled,
                "blocked_count": len(self.blocked_attempts),
                "last_blocked": last,
                "allowlist": sorted(self.allowlist),
            }


guard = NetworkGuard()
