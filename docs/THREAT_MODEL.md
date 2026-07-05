# Threat Model (summary)

**Assets:** user documents, conversation history, memories, preferences.
**Adversaries considered:** malicious imported files (zip bombs, traversal
archives, oversized/unsupported files); application code accidentally or
deliberately calling remote endpoints; stale data resurfacing after deletion.
**Mitigations:** validation + safe extraction (tested); Network Guard +
documented OS-firewall layer; query-time deletion filters (tested); audit log.
**Out of scope (documented):** a local attacker with the user's OS account;
child-process network escape (OS firewall covers this); side channels.
