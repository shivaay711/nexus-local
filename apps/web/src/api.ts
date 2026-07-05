// Typed client for the NEXUS Local API. Field names mirror the FastAPI
// responses exactly (see src/nexus_local/api/app.py).

export interface Evidence {
  chunk_id: string
  document_id: string
  source_file: string
  source_path: string
  page: number | null
  heading: string | null
  excerpt: string
  retrieval_score: number
  dense_score: number | null
  bm25_score: number | null
  embedding_model: string
}

export interface EvidenceBundle {
  query: string
  evidences: Evidence[]
  created_at: string
  index_version: string
  prompt_template_version: string
  stage_latency_ms: Record<string, number>
}

export interface AskResult {
  answer: string
  answer_source: string
  evidence_bundle: EvidenceBundle
  applied_preferences: string[]
  applied_memory_ids: string[]
  adapter: string
}

export interface Health {
  status: string
  offline_mode: string
  online?: boolean
  network_guard: boolean
  llm_adapter: string
}

export interface Memory {
  id: string
  content: string
  type: string
  state: string
  sensitivity: string
}

export interface Diagnostics {
  platform: string
  python: string
  gpu_cuda_available: boolean
  disk_free_gb: number
  documents: number
  conversations: number
  active_memories: number
  blocked_network_attempts: number
}

export interface DocumentRow {
  id: string
  filename: string
  sha256: string
  media_type: string
  parser: string
  parser_confidence: number
}

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => fetch('/api/v1/health').then(j<Health>),
  diagnostics: () => fetch('/api/v1/system/diagnostics').then(j<Diagnostics>),
  guard: () => fetch('/api/v1/security/network-guard').then(j<{ enabled: boolean; blocked_count: number; last_blocked: unknown }>),

  ask: (query: string, strict_grounding: boolean, memory_enabled: boolean) =>
    fetch('/api/v1/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, strict_grounding, memory_enabled }),
    }).then(j<AskResult>),

  documents: () => fetch('/api/v1/documents').then(j<DocumentRow[]>),

  memories: (state?: string) =>
    fetch('/api/v1/memories' + (state ? `?state=${state}` : '')).then(j<Memory[]>),
  proposeMemory: (content: string, memory_type: string) =>
    fetch('/api/v1/memories/propose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, memory_type }),
    }).then(j<{ id: string; state: string; sensitivity: string }>),
  approveMemory: (id: string) =>
    fetch(`/api/v1/memories/${id}/approve`, { method: 'POST' }).then(j<{ id: string; state: string }>),
  rejectMemory: (id: string) =>
    fetch(`/api/v1/memories/${id}/reject`, { method: 'POST' }).then(j<{ id: string; state: string }>),
  deleteMemory: (id: string) =>
    fetch(`/api/v1/memories/${id}`, { method: 'DELETE' }).then((r) => {
      if (!r.ok) throw new Error(String(r.status))
    }),
  whyMemory: (id: string) => fetch(`/api/v1/memories/${id}/why`).then(j<Record<string, unknown>>),
}

// ---- v2 additions: conversations, mode, chat turns ----
export interface ConversationRow { id: string; title: string; strict_grounding: boolean; created_at: string }
export interface WebResult { title: string; snippet: string; url: string }
export interface TurnResult extends AskResult {
  web_results: WebResult[] | null
  proposed_memory_ids: string[] | null
}
export interface MessageRow { id: string; role: string; content: string; answer_source: string | null }

export const api2 = {
  setMode: (online: boolean) =>
    fetch('/api/v1/mode', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ online }),
    }).then((r) => r.json() as Promise<{ online: boolean; network_guard: boolean }>),
  conversations: () => fetch('/api/v1/conversations').then((r) => r.json() as Promise<ConversationRow[]>),
  createConversation: (strict_grounding: boolean) =>
    fetch('/api/v1/conversations', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'Untitled', strict_grounding, memory_enabled: true }),
    }).then((r) => r.json() as Promise<{ id: string; title: string }>),
  deleteConversation: (id: string) => fetch(`/api/v1/conversations/${id}`, { method: 'DELETE' }),
  messages: (id: string) => fetch(`/api/v1/conversations/${id}/messages`).then((r) => r.json() as Promise<MessageRow[]>),
  sendMessage: (id: string, content: string) =>
    fetch(`/api/v1/conversations/${id}/messages`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    }).then(async (r) => { if (!r.ok) throw new Error(await r.text()); return r.json() as Promise<TurnResult> }),
}
