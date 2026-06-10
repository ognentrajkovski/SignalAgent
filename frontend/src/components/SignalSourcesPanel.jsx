import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Radio, Plus, Link2, Trash2, Loader2, AlertCircle, Users } from 'lucide-react'
import { addSignalSource, getSignalSources } from '../api'

// Mock source list with lead counts since backend doesn't have GET /signal-sources yet
function useSources() {
  const qc = useQueryClient()
  const [localSources, setLocalSources] = useState([])

  const mutation = useMutation({
    mutationFn: addSignalSource,
    onSuccess: (data) => {
      setLocalSources((prev) => [...prev, { ...data, leadCount: 0 }])
      qc.invalidateQueries(['leads'])
    },
  })

  return { sources: localSources, add: mutation.mutateAsync, isPending: mutation.isPending, error: mutation.error }
}

export default function SignalSourcesPanel() {
  const [url, setUrl] = useState('')
  const { sources, add, isPending, error } = useSources()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!url.trim()) return
    try {
      await add(url.trim())
      setUrl('')
    } catch (_) {}
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
          <div style={{
            width: 40, height: 40, borderRadius: 12,
            background: 'linear-gradient(135deg, var(--cyan), var(--purple))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 20px rgba(80,40,200,0.35)',
          }}>
            <Radio size={18} color="#fff" />
          </div>
          <h1 className="page-title">Signal Sources</h1>
        </div>
        <p className="page-sub">Add LinkedIn post URLs or accounts to monitor for qualified leads</p>
      </div>

      {/* Add Source Form */}
      <div className="glass" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: 'var(--text-lg)', marginBottom: '1rem', color: 'var(--t1)' }}>
          Add a new source
        </h2>
        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.75rem' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Link2
              size={14}
              style={{
                position: 'absolute', left: '0.85rem', top: '50%',
                transform: 'translateY(-50%)', color: 'var(--t3)',
              }}
            />
            <input
              id="signal-source-url"
              className="input"
              style={{ paddingLeft: '2.25rem' }}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://linkedin.com/posts/... or linkedin.com/in/username"
              type="url"
            />
          </div>
          <button
            id="add-source-btn"
            type="submit"
            className="btn btn-primary"
            disabled={isPending || !url.trim()}
          >
            {isPending ? <Loader2 size={15} style={{ animation: 'spin 0.7s linear infinite' }} /> : <Plus size={15} />}
            {isPending ? 'Adding…' : 'Add Source'}
          </button>
        </form>

        {error && (
          <div className="error-box" style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={14} />
            {error.response?.data?.detail ?? error.message}
          </div>
        )}
      </div>

      {/* Source list */}
      <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: 'var(--text-lg)' }}>Active Sources</h2>
        <span className="chip">
          <Users size={12} /> {sources.length} watching
        </span>
      </div>

      {sources.length === 0 ? (
        <div className="glass empty-state">
          <Radio size={40} />
          <p style={{ fontSize: 'var(--text-lg)', color: 'var(--t2)' }}>No sources yet</p>
          <p style={{ fontSize: 'var(--text-sm)' }}>Add a LinkedIn post or profile URL above to start tracking signals</p>
        </div>
      ) : (
        <div className="source-list">
          {sources.map((src, i) => (
            <SourceCard key={src.id ?? i} source={src} />
          ))}
        </div>
      )}

      {/* Stats strip */}
      {sources.length > 0 && (
        <div
          className="glass"
          style={{
            marginTop: '2rem',
            padding: '1.25rem 1.5rem',
            display: 'grid',
            gridTemplateColumns: 'repeat(3,1fr)',
            gap: '1rem',
          }}
        >
          <Stat label="Sources active" value={sources.length} color="var(--cyan)" />
          <Stat label="Total leads found" value={sources.reduce((s, x) => s + (x.leadCount ?? 0), 0)} color="var(--purple)" />
          <Stat label="Avg leads / source" value={sources.length ? Math.round(sources.reduce((s, x) => s + (x.leadCount ?? 0), 0) / sources.length) : 0} color="var(--amber)" />
        </div>
      )}
    </div>
  )
}

function SourceCard({ source }) {
  return (
    <div className="source-item">
      <div style={{
        width: 36, height: 36, borderRadius: 10, flexShrink: 0,
        background: 'linear-gradient(135deg, rgba(80,180,255,0.15), rgba(140,80,255,0.15))',
        border: '1px solid rgba(80,180,255,0.2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Link2 size={14} color="var(--cyan)" />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="source-url truncate">{source.url}</div>
        <div style={{ fontSize: 'var(--text-sm)', color: 'var(--t3)', marginTop: 2 }}>
          ID: {source.id} · LinkedIn Signal
        </div>
      </div>
      <div className="source-count">
        <Users size={11} style={{ display: 'inline', marginRight: 4 }} />
        {source.leadCount ?? 0} leads
      </div>
    </div>
  )
}

function Stat({ label, value, color }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 'var(--text-2xl)', fontFamily: 'var(--font-display)', fontWeight: 700, color }}>
        {value}
      </div>
      <div style={{ fontSize: 'var(--text-sm)', color: 'var(--t3)', marginTop: 4 }}>{label}</div>
    </div>
  )
}
