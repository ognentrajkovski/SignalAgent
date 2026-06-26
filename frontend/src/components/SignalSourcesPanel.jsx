import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Radio, Plus, Link2, Loader2, AlertCircle, Users, Trash2 } from 'lucide-react'
import { addSignalSource, deleteSignalSource, getLeads, getSignalSources } from '../api'

function useSources() {
  const qc = useQueryClient()

  const sourcesQuery = useQuery({
    queryKey: ['signal-sources'],
    queryFn: getSignalSources,
  })

  const leadsQuery = useQuery({
    queryKey: ['leads'],
    queryFn: getLeads,
  })

  const addMutation = useMutation({
    mutationFn: addSignalSource,
    onSuccess: (source) => {
      qc.setQueryData(['signal-sources'], (current = []) => {
        if (current.some((item) => String(item.id) === String(source.id))) return current
        return [source, ...current]
      })
      qc.invalidateQueries({ queryKey: ['signal-sources'] })
      qc.invalidateQueries({ queryKey: ['leads'] })
      qc.invalidateQueries({ queryKey: ['strategy'] })
      qc.invalidateQueries({ queryKey: ['graph'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteSignalSource,
    onMutate: async (sourceId) => {
      await qc.cancelQueries({ queryKey: ['signal-sources'] })
      await qc.cancelQueries({ queryKey: ['leads'] })

      const previousSources = qc.getQueryData(['signal-sources'])
      const previousLeads = qc.getQueryData(['leads'])
      const deletedSource = previousSources?.find((source) => String(source.id) === String(sourceId))

      qc.setQueryData(['signal-sources'], (current = []) =>
        current.filter((source) => String(source.id) !== String(sourceId))
      )

      if (deletedSource) {
        qc.setQueryData(['leads'], (current = []) =>
          current.filter((lead) => (lead.source ?? lead.signal) !== deletedSource.url)
        )
      }

      return { previousSources, previousLeads }
    },
    onError: (_error, _sourceId, context) => {
      if (context?.previousSources) {
        qc.setQueryData(['signal-sources'], context.previousSources)
      }
      if (context?.previousLeads) {
        qc.setQueryData(['leads'], context.previousLeads)
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['signal-sources'] })
      qc.invalidateQueries({ queryKey: ['leads'] })
      qc.invalidateQueries({ queryKey: ['strategy'] })
      qc.invalidateQueries({ queryKey: ['graph'] })
    },
  })

  const addSource = async (url) => {
    const data = await addMutation.mutateAsync(url)
    return data
  }

  const leadCountsBySource = (leadsQuery.data ?? []).reduce((counts, lead) => {
    const source = lead.source ?? lead.signal
    if (!source) return counts
    counts[source] = (counts[source] ?? 0) + 1
    return counts
  }, {})

  const sources = (sourcesQuery.data ?? []).map((source) => ({
    ...source,
    lead_count: leadCountsBySource[source.url] ?? source.lead_count ?? 0,
  }))

  return {
    sources,
    add: addSource,
    remove: (id) => deleteMutation.mutate(id),
    isLoading: sourcesQuery.isLoading || leadsQuery.isLoading,
    isPending: addMutation.isPending,
    deletingId: deleteMutation.variables,
    isDeleting: deleteMutation.isPending,
    error: addMutation.error ?? deleteMutation.error ?? sourcesQuery.error ?? leadsQuery.error,
  }
}

export default function SignalSourcesPanel() {
  const [url, setUrl] = useState('')
  const { sources, add, remove, isLoading, isPending, deletingId, isDeleting, error } = useSources()
  const totalLeads = sources.reduce((sum, source) => sum + getLeadCount(source), 0)

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

      {isLoading ? (
        <div className="loading-wrap">
          <Loader2 size={22} style={{ animation: 'spin 0.7s linear infinite', color: 'var(--cyan)' }} />
          <span>Loading sources...</span>
        </div>
      ) : sources.length === 0 ? (
        <div className="glass empty-state">
          <Radio size={40} />
          <p style={{ fontSize: 'var(--text-lg)', color: 'var(--t2)' }}>No sources yet</p>
          <p style={{ fontSize: 'var(--text-sm)' }}>Add a LinkedIn post or profile URL above to start tracking signals</p>
        </div>
      ) : (
        <div className="source-list">
          {sources.map((src, i) => (
            <SourceCard
              key={src.id ?? i}
              source={src}
              onDelete={remove}
              isDeleting={isDeleting && String(deletingId) === String(src.id)}
            />
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
          <Stat label="Total leads found" value={totalLeads} color="var(--purple)" />
          <Stat label="Avg leads / source" value={sources.length ? Math.round(totalLeads / sources.length) : 0} color="var(--amber)" />
        </div>
      )}
    </div>
  )
}

function SourceCard({ source, onDelete, isDeleting }) {
  return (
    <div className="source-item" style={{ opacity: isDeleting ? 0.55 : 1, transition: 'opacity 0.2s' }}>
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
          LinkedIn Signal
        </div>
      </div>
      <div className="source-count">
        <Users size={11} style={{ display: 'inline', marginRight: 4 }} />
        {getLeadCount(source)} leads
      </div>
      <button
        type="button"
        className="btn btn-ghost btn-sm"
        title={`Delete source ${source.id}`}
        disabled={isDeleting}
        onClick={() => onDelete(source.id)}
        style={{
          color: 'var(--red)',
          padding: '0.35rem',
          borderRadius: 6,
          flexShrink: 0,
        }}
      >
        {isDeleting
          ? <Loader2 size={13} style={{ animation: 'spin 0.7s linear infinite' }} />
          : <Trash2 size={13} />}
      </button>
    </div>
  )
}

function getLeadCount(source) {
  return source.lead_count ?? source.leadCount ?? 0
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
