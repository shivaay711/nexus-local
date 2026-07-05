"""Runtime mode: OFFLINE (default, Network Guard on) vs ONLINE (guard off,
web search available). Mode changes are explicit user actions, audited, and
never persist across restarts — the app always boots offline-first."""
from __future__ import annotations

import re
import threading

from ..db import audit, get_session
from ..security.network_guard import guard

_lock = threading.Lock()
_online = False


def is_online() -> bool:
    return _online


def set_online(online: bool) -> dict:
    global _online
    with _lock:
        if online:
            guard.disable()
        else:
            guard.enable()
        _online = online
    with get_session() as s:
        audit(s, "mode_change", "system", "runtime", "online" if online else "offline")
        s.commit()
    return {"online": _online, "network_guard": guard.enabled}


# ------------------------------------------------------------ auto-memory
# Heuristics that detect self-disclosures worth remembering. They only ever
# PROPOSE — the approval gate stays intact.
_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bmy name is ([^.,!?\n]{2,40})", re.I), "profile"),
    (re.compile(r"\bcall me ([^.,!?\n]{2,30})", re.I), "profile"),
    (re.compile(r"\bi (?:am|'m) (?:a|an) ([^.,!?\n]{3,60})", re.I), "profile"),
    (re.compile(r"\bi prefer ([^.!?\n]{3,80})", re.I), "preference"),
    (re.compile(r"\bi like ([^.!?\n]{3,80})", re.I), "preference"),
    (re.compile(r"\bi work (?:at|on|in) ([^.,!?\n]{3,60})", re.I), "profile"),
    (re.compile(r"\bi study ([^.,!?\n]{3,60})", re.I), "study"),
    (re.compile(r"\bi(?:'m| am) (?:building|working on) ([^.!?\n]{3,80})", re.I), "project"),
    (re.compile(r"\bmy goal is ([^.!?\n]{3,80})", re.I), "goal"),
]


def propose_memories_from_text(text: str, source_conversation_id: str | None = None) -> list[str]:
    """Scan a user message for self-disclosures; propose (not activate) each.
    Returns proposed memory IDs so the UI can offer one-tap approval."""
    from ..memory.service import propose_memory
    proposed: list[str] = []
    seen: set[str] = set()
    for rx, mtype in _PATTERNS:
        for m in rx.finditer(text):
            content = m.group(0).strip()
            key = content.lower()
            if key in seen or len(content) < 8:
                continue
            seen.add(key)
            mem = propose_memory(content=f"User said: {content}", memory_type=mtype,
                                 source_conversation_id=source_conversation_id,
                                 confidence=0.6)
            proposed.append(mem.id)
    return proposed
