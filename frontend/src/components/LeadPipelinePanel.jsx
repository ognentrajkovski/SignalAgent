import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Users, AlertTriangle, CheckCircle, TrendingUp, ChevronRight, Loader2 } from 'lucide-react'
import { getLeads } from '../api'

const MOCK_LEADS = [
  { id: 1, person_id: 'p_001', name: 'Alex Chen', company: 'Stripe', role: 'Staff Engineer', gnn_score: 0.91, llm_score: 0.62, disagreement_flag: true, qualified: true, signal: 'linkedin.com/posts/react-2024' },
  { id: 2, person_id: 'p_002', name: 'Maya Patel', company: 'Vercel', role: 'Engineering Manager', gnn_score: 0.87, llm_score: 0.85, disagreement_flag: false, qualified: true, signal: 'linkedin.com/posts/nextjs-conf' },
  { id: 3, person_id: 'p_003', name: 'Jordan Kim', company: 'Figma', role: 'Senior PM', gnn_score: 0.44, llm_score: 0.78, disagreement_flag: true, qualified: true, signal: 'linkedin.com/in/jordankim' },
  { id: 4, person_id: 'p_004', name: 'Sam Rivera', company: 'Linear', role: 'CTO', gnn_score: 0.95, llm_score: 0.93, disagreement_flag: false, qualified: true, signal: 'linkedin.com/posts/linear-launch' },
  { id: 5, person_id: 'p_005', name: 'Dana Wu', company: 'Notion', role: 'VP Product', gnn_score: 0.29, llm_score: 0.31, disagreement_flag: false, qualified: false, signal: 'linkedin.com/in/danawu' },
  { id: 6, person_id: 'p_006', name: 'Chris Morgan', company: 'Loom', role: 'Head of Growth', gnn_score: 0.72, llm_score: 0.41, disagreement_flag: true, qualified: true, signal: 'linkedin.com/posts/loom-series' },
]

function ScoreBar({ value, colorVar }) {
  return (
    <div className="score-bar" style={{ minWidth: 100 }}>
      <div className="score-track">
        <div
          className="score-fill"
          style={{
            width: `${Math.round(value * 100)}%`,
            background: colorVar === 'cyan'
              ? 'linear-gradient(90deg, var(--cyan), rgba(80,180,255,0.6))'
              : 'linear-gradient(90deg, var(--purple), rgba(140,80,255,0.6))',
          }}
        />
      </div>
      <span style={{ width: 36, textAlign: 'right', color: 'var(--t2)', fontVariantNumeric: 'tabular-nums' }}>
        {(value * 100).toFixed(0)}%
      </span>
    </div>
  )
}

export default function LeadPipelinePanel() {
  const navigate = useNavigate()
  const { data, isLoading, error } = useQuery({
    queryKey: ['leads'],
    queryFn: getLeads,
    placeholderData: MOCK_LEADS,
  })

  const leads = (data ?? MOCK_LEADS).map((l, i) => ({
    ...MOCK_LEADS[i % MOCK_LEADS.length],
    ...l,
  }))

  const qualified = leads.filter((l) => l.qualified)
  const disagreements = leads.filter((l) => l.disagreement_flag)

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
          <div style={{
            width: 40, height: 40, borderRadius: 12,
            background: 'linear-gradient(135deg, var(--purple), var(--cyan))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 20px rgba(140,80,255,0.35)',
          }}>
            <Users size={18} color="#fff" />
          </div>
          <h1 className="page-title">Lead Pipeline</h1>
        </div>
        <p className="page-sub">Ranked qualified leads scored by both GNN and LLM models</p>
      </div>

      {/* Summary stats */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '1rem', marginBottom: '2rem',
      }}>
        <StatCard icon={<Users size={16} />} value={leads.length} label="Total Leads" color="var(--cyan)" />
        <StatCard icon={<CheckCircle size={16} />} value={qualified.length} label="Qualified" color="var(--green)" />
        <StatCard icon={<AlertTriangle size={16} />} value={disagreements.length} label="Disagreements" color="var(--amber)" />
        <StatCard icon={<TrendingUp size={16} />} value={`${qualified.length ? Math.round((qualified.length / leads.length) * 100) : 0}%`} label="Qualify Rate" color="var(--purple)" />
      </div>

      {isLoading && (
        <div className="loading-wrap">
          <Loader2 size={24} style={{ animation: 'spin 0.7s linear infinite', color: 'var(--cyan)' }} />
          <span>Loading leads…</span>
        </div>
      )}

      {error && (
        <div className="error-box" style={{ marginBottom: '1rem' }}>
          API error — showing demo data
        </div>
      )}

      {/* Table */}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Person</th>
              <th>Company</th>
              <th>Role</th>
              <th>GNN Score</th>
              <th>LLM Score</th>
              <th>Status</th>
              <th>Signal</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead) => (
              <tr
                key={lead.id}
                id={`lead-row-${lead.id}`}
                onClick={() => navigate(`/leads/${lead.id}`)}
                style={lead.disagreement_flag ? { background: 'rgba(255,180,0,0.03)' } : {}}
              >
                {/* Name */}
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <Avatar name={lead.name ?? lead.person_id} />
                    <span style={{ fontWeight: 500 }}>{lead.name ?? lead.person_id}</span>
                  </div>
                </td>
                {/* Company */}
                <td style={{ color: 'var(--t2)' }}>{lead.company ?? '—'}</td>
                {/* Role */}
                <td style={{ color: 'var(--t2)' }}>{lead.role ?? '—'}</td>
                {/* GNN */}
                <td><ScoreBar value={lead.gnn_score ?? 0} colorVar="cyan" /></td>
                {/* LLM */}
                <td><ScoreBar value={lead.llm_score ?? 0} colorVar="purple" /></td>
                {/* Status */}
                <td>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                    {lead.qualified
                      ? <span className="flag-green">✓ Qualified</span>
                      : <span style={{ fontSize: '0.65rem', color: 'var(--t3)' }}>Unqualified</span>
                    }
                    {lead.disagreement_flag && (
                      <span className="flag-amber">⚡ Disagree</span>
                    )}
                  </div>
                </td>
                {/* Signal */}
                <td>
                  <span className="truncate" style={{ maxWidth: 140, display: 'block', fontSize: 'var(--text-sm)', color: 'var(--t3)' }}>
                    {lead.signal ?? '—'}
                  </span>
                </td>
                <td>
                  <ChevronRight size={14} style={{ color: 'var(--t3)' }} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p style={{ marginTop: '0.75rem', fontSize: 'var(--text-sm)', color: 'var(--t3)', textAlign: 'right' }}>
        Click a row to view the full lead timeline ↗
      </p>
    </div>
  )
}

function Avatar({ name }) {
  const initials = (name ?? '?').split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
  const hue = [...(name ?? '')].reduce((n, c) => n + c.charCodeAt(0), 0) % 360
  return (
    <div style={{
      width: 30, height: 30, borderRadius: '50%', flexShrink: 0,
      background: `oklch(0.45 0.18 ${hue})`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: '0.65rem', fontWeight: 700, color: '#fff',
      border: '1px solid rgba(255,255,255,0.1)',
    }}>
      {initials}
    </div>
  )
}

function StatCard({ icon, value, label, color }) {
  return (
    <div className="glass" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color }}>
        {icon}
        <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600 }}>{label}</span>
      </div>
      <div style={{ fontSize: 'var(--text-2xl)', fontFamily: 'var(--font-display)', fontWeight: 700, color }}>
        {value}
      </div>
    </div>
  )
}
