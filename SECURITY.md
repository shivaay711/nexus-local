# Security

- API binds to 127.0.0.1 only; no remote authentication surface.
- Network Guard on by default in Air-Gapped mode (see docs/offline_mode.md,
  including its honest process-level limits and OS-firewall guidance).
- Upload validation: extension allowlist, size limits, empty-file rejection.
- Archive safety: path-traversal rejection, symlink rejection, member-count,
  total-size, and per-member compression-ratio limits (zip-bomb protection).
  All verified by tests.
- Sensitive-content classification on memories (emails, card-like numbers,
  PAN/Aadhaar-like patterns, credential-like text) → `sensitive` tag.
- Append-only audit log for imports, deletions, memory transitions,
  preference changes, feedback; SecurityEvent rows for blocked network calls.
- Report issues via GitHub issues on the repository.
