# Privacy

- All data (documents, chunks, embeddings, conversations, memories,
  preferences, feedback, evaluation runs) lives in a local SQLite database and
  local index files under the workspace directory. Nothing is transmitted.
- No telemetry, no analytics, no update checks, no cloud APIs. The Network
  Guard enforces this at the socket layer inside the app process and logs any
  attempt.
- Memory is opt-in by construction: the state machine makes it impossible for
  proposed memories to be retrieved before explicit approval (tested).
- Deletion is honored at query time: deleted documents are removed from the
  lexical index and filtered from retrieval; deleted memories are never
  retrieved (tested).
- Training candidates are never used automatically; they enter a proposed
  state requiring explicit approval (tested).
- Raw document content is not written to logs.
