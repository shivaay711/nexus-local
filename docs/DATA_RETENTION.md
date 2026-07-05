# Data Retention

- Documents/chunks: kept until user deletion; soft-deleted rows excluded from
  retrieval and removed from FTS; source files on disk are never deleted by
  default (references removed instead).
- Memories: state machine controls lifetime; expiry timestamps enforced at
  retrieval time; permanent deletion sets deleted flag and blocks retrieval.
- Conversations: kept until deleted by user.
- Evaluation runs and audit logs: local, exportable, deletable with the DB.
- Full wipe: delete the workspace directory (default ~/.nexus-local).
