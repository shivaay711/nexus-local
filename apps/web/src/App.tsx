import { useCallback, useEffect, useRef, useState } from 'react'
import {
  api, api2, type AskResult, type Health, type Memory, type DocumentRow,
  type ConversationRow, type TurnResult,
} from './api'

type Page = 'chat' | 'memory' | 'docs'
interface Turn {
  q: string
  result?: TurnResult
  error?: string
  pending?: boolean
}

const SOURCE_LABEL: Record<string, string> = {
  local_sources: 'Your documents',
  mixed: 'Docs + more',
  web_sources: 'Web',
  approved_memory: 'Memory',
  base_model: 'Model knowledge',
  insufficient_evidence: 'No local evidence',
}

export default function App() {
  const [page, setPage] = useState<Page>('chat')
  const [health, setHealth] = useState<Health | null>(null)
  const [convs, setConvs] = useState<ConversationRow[]>([])
  const [activeConv, setActiveConv] = useState<string | null>(null)
  const [turns, setTurns] = useState<Turn[]>([])

  const refreshHealth = useCallback(() => {
    api.health().then(setHealth).catch(() => setHealth(null))
  }, [])
  const refreshConvs = useCallback(() => {
    api2.conversations().then(setConvs).catch(() => {})
  }, [])

  useEffect(() => {
    refreshHealth(); refreshConvs()
    const t = setInterval(refreshHealth, 8000)
    return () => clearInterval(t)
  }, [refreshHealth, refreshConvs])

  const newChat = () => { setActiveConv(null); setTurns([]); setPage('chat') }

  const openConv = async (id: string) => {
    setActiveConv(id); setPage('chat')
    const msgs = await api2.messages(id)
    const rebuilt: Turn[] = []
    for (let i = 0; i < msgs.length; i++) {
      if (msgs[i].role === 'user') {
        const a = msgs[i + 1]
        rebuilt.push({
          q: msgs[i].content,
          result: a && a.role === 'assistant' ? ({
            answer: a.content, answer_source: a.answer_source ?? 'base_model',
            evidence_bundle: { query: '', evidences: [], created_at: '', index_version: '', prompt_template_version: '', stage_latency_ms: {} },
            applied_preferences: [], applied_memory_ids: [], adapter: '',
            web_results: null, proposed_memory_ids: null,
          } as TurnResult) : undefined,
        })
      }
    }
    setTurns(rebuilt)
  }

  const deleteConv = async (id: string) => {
    await api2.deleteConversation(id)
    if (id === activeConv) newChat()
    refreshConvs()
  }

  const online = !!health?.online

  return (
    <div className="app">
      <aside className="rail">
        <div className="brand"><span className="brand-mark">NEXUS<b>·</b></span></div>
        <div className="brand-sub">local · private · yours</div>
        <button className="new-chat" onClick={newChat}><span>+</span> New chat</button>
        <div className="conv-list">
          {convs.map((c) => (
            <div key={c.id} className={`conv-item ${c.id === activeConv ? 'active' : ''}`}
              onClick={() => openConv(c.id)} role="button" tabIndex={0}>
              <span className="t">{c.title}</span>
              <button className="del" onClick={(e) => { e.stopPropagation(); deleteConv(c.id) }}>✕</button>
            </div>
          ))}
        </div>
        <div className="rail-status">
          <div className="status-row">
            <span className={`dot ${health ? 'on' : 'off'}`} />
            {health ? 'Local services' : 'Backend offline'}
          </div>
          <div className="status-row">
            <span className={`dot ${online ? 'warn' : 'on'}`} />
            {online ? 'Internet: connected' : 'Air-gapped'}
            <span className="status-val">{health?.network_guard ? 'guard on' : 'guard off'}</span>
          </div>
          <div className="status-row">
            <span className="dot on" />
            <span className="status-val" style={{ marginLeft: 0 }}>{health?.llm_adapter ?? '—'}</span>
          </div>
          <div className="rail-nav">
            <button className={page === 'chat' ? 'active' : ''} onClick={() => setPage('chat')}>Chat</button>
            <button className={page === 'memory' ? 'active' : ''} onClick={() => setPage('memory')}>Memory</button>
            <button className={page === 'docs' ? 'active' : ''} onClick={() => setPage('docs')}>Docs</button>
          </div>
        </div>
      </aside>

      <div className="main">
        {page === 'chat' && (
          <ChatView
            health={health} refreshHealth={refreshHealth}
            activeConv={activeConv} setActiveConv={setActiveConv}
            turns={turns} setTurns={setTurns} refreshConvs={refreshConvs}
          />
        )}
        {page === 'memory' && <MemoryCenter />}
        {page === 'docs' && <DocLibrary />}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ chat */
function ChatView({ health, refreshHealth, activeConv, setActiveConv, turns, setTurns, refreshConvs }: {
  health: Health | null
  refreshHealth: () => void
  activeConv: string | null
  setActiveConv: (id: string) => void
  turns: Turn[]
  setTurns: React.Dispatch<React.SetStateAction<Turn[]>>
  refreshConvs: () => void
}) {
  const [input, setInput] = useState('')
  const [strict, setStrict] = useState(false)
  const [inspect, setInspect] = useState<AskResult | null>(null)
  const [busyMode, setBusyMode] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const online = !!health?.online

  useEffect(() => { scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight) }, [turns])

  const setMode = async (wantOnline: boolean) => {
    if (busyMode || wantOnline === online) return
    setBusyMode(true)
    try { await api2.setMode(wantOnline); refreshHealth() } finally { setBusyMode(false) }
  }

  const send = async () => {
    const q = input.trim()
    if (!q) return
    setInput('')
    let convId = activeConv
    try {
      if (!convId) {
        const c = await api2.createConversation(strict)
        convId = c.id
        setActiveConv(convId)
      }
      const idx = turns.length
      setTurns((t) => [...t, { q, pending: true }])
      const result = await api2.sendMessage(convId, q)
      setTurns((t) => t.map((x, i) => (i === idx ? { q, result } : x)))
      refreshConvs()
    } catch (e) {
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { q, error: String(e) } : x)))
    }
  }

  return (
    <>
      <div className="main-head">
        <div className="main-title">
          {activeConv ? 'Chat' : 'New chat'}
          <span>{health?.llm_adapter ?? ''}</span>
        </div>
        <div className="head-right">
          <label className="toggle" onClick={() => setStrict((s) => !s)} title="Only answer from your documents">
            <span className={`switch ${strict ? 'on' : ''}`} /> Docs only
          </label>
          <div className="mode-pill">
            <button className={!online ? 'sel-off' : ''} onClick={() => setMode(false)} disabled={busyMode}>Offline</button>
            <button className={online ? 'sel-on' : ''} onClick={() => setMode(true)} disabled={busyMode}>Online</button>
          </div>
        </div>
      </div>

      <div className="panel" ref={scrollRef}>
        <div className="chat-scroll">
          {turns.length === 0 && (
            <p className="empty">
              Ask me anything.
              <small>
                Offline: private, answers from the model + your docs.<br />
                Online: adds live web search. "Docs only" forces strict grounding.
              </small>
            </p>
          )}
          {turns.map((t, i) => <TurnBlock key={i} t={t} onInspect={(r) => setInspect(r)} />)}
        </div>
      </div>

      <div className="composer-wrap">
        <div className="composer">
          <textarea
            value={input}
            placeholder="Message NEXUS…"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          />
          <button className="send" onClick={send} disabled={!input.trim()}>Send</button>
        </div>
        <div className="composer-hint">
          {online ? 'online — web search enabled, network guard off' : 'offline — everything stays on this machine'}
        </div>
      </div>

      <Inspector result={inspect} onClose={() => setInspect(null)} />
    </>
  )
}

function TurnBlock({ t, onInspect }: { t: Turn; onInspect: (r: AskResult) => void }) {
  const r = t.result
  const refusal = r?.answer_source === 'insufficient_evidence'
  const evs = r?.evidence_bundle?.evidences ?? []
  return (
    <>
      <div className="msg msg-user">
        <div className="avatar user">R</div>
        <div className="msg-body">{t.q}</div>
      </div>
      <div className="msg msg-ai">
        <div className="avatar ai">N</div>
        <div className="msg-body-wrap" style={{ minWidth: 0, flex: 1 }}>
          {t.pending && <div className="spin">thinking…</div>}
          {t.error && <div className="err">{t.error}</div>}
          {r && (
            <>
              <div className={`msg-body ${refusal ? 'refusal' : ''}`}>{r.answer}</div>
              <div className="answer-meta">
                <span className={`chip src-${r.answer_source}`}>{SOURCE_LABEL[r.answer_source] ?? r.answer_source}</span>
                {evs.length > 0 && (
                  <span className="chip link" onClick={() => onInspect(r)}>
                    {evs.length} local source{evs.length > 1 ? 's' : ''} ↗
                  </span>
                )}
              </div>
              {r.web_results && r.web_results.length > 0 && (
                <div className="web-cites">
                  {r.web_results.map((w, i) => (
                    <div className="web-cite" key={i}>
                      <a href={w.url} target="_blank" rel="noreferrer">[W{i + 1}] {w.title}</a>
                    </div>
                  ))}
                </div>
              )}
              {r.proposed_memory_ids && r.proposed_memory_ids.length > 0 && (
                <MemoryBanner ids={r.proposed_memory_ids} />
              )}
            </>
          )}
        </div>
      </div>
    </>
  )
}

function MemoryBanner({ ids }: { ids: string[] }) {
  const [state, setState] = useState<'ask' | 'saved' | 'dismissed'>('ask')
  if (state === 'dismissed') return null
  if (state === 'saved') return <div className="mem-banner"><span className="txt">Saved to memory. I'll remember this.</span></div>
  return (
    <div className="mem-banner">
      <span className="txt">I noticed something about you worth remembering ({ids.length} item{ids.length > 1 ? 's' : ''}). Save it?</span>
      <button onClick={async () => { await Promise.all(ids.map((id) => api.approveMemory(id))); setState('saved') }}>Remember</button>
      <button onClick={async () => { await Promise.all(ids.map((id) => api.rejectMemory(id))); setState('dismissed') }}>No thanks</button>
    </div>
  )
}

/* --------------------------------------------------------- inspector */
function Inspector({ result, onClose }: { result: AskResult | null; onClose: () => void }) {
  const b = result?.evidence_bundle
  return (
    <div className={`drawer ${result ? 'open' : ''}`}>
      <div className="drawer-head">
        <h3>Why this answer</h3>
        <button onClick={onClose}>close</button>
      </div>
      {b && (
        <div className="drawer-body">
          <div className="stage-lat">
            {Object.entries(b.stage_latency_ms).map(([k, v]) => (
              <div className="lat-cell" key={k}><div className="k">{k}</div><div className="v">{v} ms</div></div>
            ))}
          </div>
          {b.evidences.map((e, i) => (
            <div className="ev" key={e.chunk_id}>
              <div className="ev-head">
                <span className="ev-num">[{i + 1}]</span>
                <span className="ev-file">{e.source_file}</span>
                <span className="ev-page">{e.page != null ? `p.${e.page}` : ''}</span>
              </div>
              <div className="ev-excerpt">{e.excerpt}</div>
              <div className="ev-scores">
                <span><b>rrf</b> {e.retrieval_score.toFixed(4)}</span>
                {e.dense_score != null && <span><b>dense</b> {e.dense_score.toFixed(3)}</span>}
                {e.bm25_score != null && <span><b>bm25</b> {e.bm25_score.toFixed(2)}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* --------------------------------------------------------- memory page */
const MEM_TYPES = ['preference', 'profile', 'project', 'study', 'work_style',
  'communication_style', 'instruction', 'goal', 'constraint']

function MemoryCenter() {
  const [mems, setMems] = useState<Memory[]>([])
  const [content, setContent] = useState('')
  const [type, setType] = useState('preference')
  const [err, setErr] = useState('')

  const load = () => api.memories().then(setMems).catch((e) => setErr(String(e)))
  useEffect(() => { load() }, [])

  const propose = async () => {
    if (!content.trim()) return
    try { await api.proposeMemory(content.trim(), type); setContent(''); load() }
    catch (e) { setErr(String(e)) }
  }
  const act = async (fn: Promise<unknown>) => { try { await fn; load() } catch (e) { setErr(String(e)) } }

  return (
    <div className="panel">
      <div className="page-pad">
        <p className="section-note">
          What NEXUS knows about you. It proposes memories from your chats but never saves
          without your OK. Only <b>active</b> memories shape answers. Delete is permanent.
        </p>
        <div className="propose-box">
          <textarea value={content} onChange={(e) => setContent(e.target.value)}
            placeholder="Tell it something to remember, e.g. I prefer short direct answers" style={{ minHeight: 44 }} />
          <div className="row">
            <select value={type} onChange={(e) => setType(e.target.value)}>
              {MEM_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <button onClick={propose} disabled={!content.trim()}>Propose memory</button>
          </div>
        </div>
        {err && <div className="err">{err}</div>}
        {mems.length === 0 && <p className="section-note">Nothing remembered yet.</p>}
        {mems.map((m) => (
          <div className="mem" key={m.id}>
            <div className="mem-top">
              <span className="mem-type">{m.type}</span>
              <span className={`mem-state ${m.state}`}>{m.state}</span>
              {m.sensitivity === 'sensitive' && <span className="mem-sens">⚠ sensitive</span>}
            </div>
            <div className="mem-content">{m.content}</div>
            <div className="mem-actions">
              {m.state === 'proposed' && <>
                <button onClick={() => act(api.approveMemory(m.id))}>Approve</button>
                <button onClick={() => act(api.rejectMemory(m.id))}>Reject</button>
              </>}
              <button className="danger" onClick={() => act(api.deleteMemory(m.id))}>Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* --------------------------------------------------------- docs page */
function DocLibrary() {
  const [docs, setDocs] = useState<DocumentRow[]>([])
  const [err, setErr] = useState('')
  useEffect(() => { api.documents().then(setDocs).catch((e) => setErr(String(e))) }, [])
  return (
    <div className="panel">
      <div className="page-pad">
        <p className="section-note">
          {docs.length} documents indexed locally. Import more with{' '}
          <code style={{ fontFamily: 'var(--mono)', color: 'var(--signal)' }}>python scripts/import_folder.py &lt;folder&gt;</code>.
        </p>
        {err && <div className="err">{err}</div>}
        {docs.map((d) => {
          const conf = d.parser_confidence >= 0.85 ? 'high' : d.parser_confidence >= 0.5 ? 'mid' : 'low'
          return (
            <div className="doc-row" key={d.id}>
              <span className="doc-name">{d.filename}</span>
              <span className="doc-meta">{d.parser} · {d.media_type}</span>
              <span className={`doc-conf ${conf}`}>{(d.parser_confidence * 100).toFixed(0)}%</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
