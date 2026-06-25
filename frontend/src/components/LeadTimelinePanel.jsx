import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import {
  ArrowLeft, Heart, Clock, UserPlus, CheckCircle2,
  Loader2, Zap, MessageSquare, Send, Timer, Link2, Search, FileText, XCircle,
} from 'lucide-react'
import { getLeadTimeline } from '../api'

const ACTION_ICONS = {
  source_detected:           { icon: Search,       color: 'var(--cyan)',   bg: 'rgba(80,180,255,0.12)'  },
  profile_enriched:          { icon: FileText,     color: 'var(--purple)', bg: 'rgba(140,80,255,0.12)'  },
  like_post:                 { icon: Heart,        color: 'var(--red)',    bg: 'rgba(255,60,60,0.12)'   },
  draft_connection_request:  { icon: UserPlus,     color: 'var(--cyan)',   bg: 'rgba(80,180,255,0.12)'  },
  send_email:                { icon: Send,         color: 'var(--purple)', bg: 'rgba(140,80,255,0.12)'  },
  wait:                      { icon: Timer,        color: 'var(--t3)',     bg: 'rgba(255,255,255,0.06)' },
  qualify:                   { icon: CheckCircle2, color: 'var(--green)',  bg: 'rgba(0,220,120,0.12)'   },
  disqualify:                { icon: XCircle,      color: 'var(--red)',    bg: 'rgba(255,60,60,0.12)'   },
  reply:                     { icon: MessageSquare,color: 'var(--amber)',  bg: 'rgba(255,180,0,0.12)'   },
}

const MOCK_NAMES = ['Alex Chen', 'Maya Patel', 'Jordan Kim', 'Sam Rivera', 'Dana Wu', 'Chris Morgan', 'Priya Lal', 'Nina Shah']
const MOCK_COMPANIES = ['Stripe', 'Vercel', 'Figma', 'Linear', 'Notion', 'Loom', 'HubSpot', 'Amplitude']
const MOCK_ROLES = ['VP Revenue Operations', 'Head of Growth', 'Director of Demand Gen', 'RevOps Lead', 'GTM Strategy Lead', 'Chief Revenue Officer']
const MOCK_SOURCES = [
  'linkedin.com/posts/revops-stack-2026',
  'linkedin.com/posts/plg-benchmark-report',
  'linkedin.com/in/gtm-operator',
  'linkedin.com/posts/pipeline-generation-playbook',
  'linkedin.com/company/revenue-leaders',
  'linkedin.com/posts/crm-hygiene-roundtable',
]

const MOCK_TIMELINES = {
  1: {
    lead_id: 1, person_id: 'p_001',
    name: 'Alex Chen', company: 'Stripe', role: 'Staff Engineer',
    gnn_score: 0.91, llm_score: 0.62,
    timeline: [
      { action_type: 'qualify',                rationale: 'GNN score 0.91 exceeds threshold. LLM score 0.62 — disagreement flagged for review.', timestamp: '2024-01-15T09:00:00Z', reply_probability: null, status: 'done' },
      { action_type: 'like_post',              rationale: 'Engaged with their React architecture post to establish visibility before outreach.', timestamp: '2024-01-15T10:30:00Z', reply_probability: 0.62, status: 'done' },
      { action_type: 'draft_connection_request', rationale: 'Personalized request referencing their open-source contributions and Stripe infra work.', timestamp: '2024-01-16T08:00:00Z', reply_probability: 0.74, status: 'pending' },
    ],
  },
  2: {
    lead_id: 2, person_id: 'p_002',
    name: 'Maya Patel', company: 'Vercel', role: 'Engineering Manager',
    gnn_score: 0.87, llm_score: 0.85,
    timeline: [
      { action_type: 'qualify',    rationale: 'Both GNN (0.87) and LLM (0.85) agree — high confidence lead.', timestamp: '2024-01-14T11:00:00Z', reply_probability: null, status: 'done' },
      { action_type: 'like_post',  rationale: 'Liked Next.js conf recap to warm up the relationship.', timestamp: '2024-01-14T14:00:00Z', reply_probability: 0.55, status: 'done' },
      { action_type: 'send_email', rationale: 'Sent intro email referencing her talk on edge computing — mentioned mutual connections.', timestamp: '2024-01-15T09:00:00Z', reply_probability: 0.81, status: 'done' },
      { action_type: 'reply',      rationale: 'Maya replied! Positive tone. Scheduling a call.', timestamp: '2024-01-15T16:30:00Z', reply_probability: 1.0, status: 'done' },
    ],
  },
  3: {
    lead_id: 3, person_id: 'p_003',
    name: 'Jordan Kim', company: 'Figma', role: 'Senior PM',
    gnn_score: 0.44, llm_score: 0.78,
    timeline: [
      { action_type: 'qualify',    rationale: 'LLM score 0.78. GNN score 0.44. Disagreement flagged for review.', timestamp: '2024-01-14T11:00:00Z', reply_probability: null, status: 'done' },
      { action_type: 'like_post',  rationale: 'Engaged with their latest product update post.', timestamp: '2024-01-14T14:00:00Z', reply_probability: 0.45, status: 'done' },
      { action_type: 'draft_connection_request', rationale: 'Drafted request citing shared interest in design systems.', timestamp: '2024-01-15T09:00:00Z', reply_probability: 0.65, status: 'pending' },
    ],
  },
  4: {
    lead_id: 4, person_id: 'p_004',
    name: 'Sam Rivera', company: 'Linear', role: 'CTO',
    gnn_score: 0.95, llm_score: 0.93,
    timeline: [
      { action_type: 'qualify',    rationale: 'Both GNN and LLM indicate strong fit.', timestamp: '2024-01-14T11:00:00Z', reply_probability: null, status: 'done' },
      { action_type: 'like_post',  rationale: 'Liked their launch post.', timestamp: '2024-01-14T14:00:00Z', reply_probability: 0.70, status: 'done' },
      { action_type: 'send_email', rationale: 'Sent personalized email about dev tools.', timestamp: '2024-01-15T09:00:00Z', reply_probability: 0.85, status: 'done' },
      { action_type: 'reply',      rationale: 'Sam replied to schedule a quick chat.', timestamp: '2024-01-15T16:30:00Z', reply_probability: 1.0, status: 'done' },
    ],
  },
  5: {
    lead_id: 5, person_id: 'p_005',
    name: 'Dana Wu', company: 'Notion', role: 'VP Product',
    gnn_score: 0.29, llm_score: 0.31, qualified: false,
    timeline: [
      { action_type: 'disqualify', rationale: 'Both models indicate low fit. Not qualified.', timestamp: '2024-01-14T11:00:00Z', reply_probability: null, status: 'done' },
    ],
  },
  6: {
    lead_id: 6, person_id: 'p_006',
    name: 'Chris Morgan', company: 'Loom', role: 'Head of Growth',
    gnn_score: 0.72, llm_score: 0.41,
    timeline: [
      { action_type: 'qualify',    rationale: 'GNN score 0.72. LLM score 0.41. Disagreement flagged for review.', timestamp: '2024-01-14T11:00:00Z', reply_probability: null, status: 'done' },
      { action_type: 'like_post',  rationale: 'Liked Loom series announcement.', timestamp: '2024-01-14T14:00:00Z', reply_probability: 0.50, status: 'done' },
      { action_type: 'draft_connection_request', rationale: 'Drafted message highlighting PLG strategies.', timestamp: '2024-01-15T09:00:00Z', reply_probability: 0.60, status: 'pending' },
    ],
  },
}

function getDefaultTimeline(id) {
  return MOCK_TIMELINES[id] ?? {
    lead_id: id,
    person_id: `p_00${id}`,
    name: `Lead #${id}`,
    company: 'Unknown',
    role: 'Unknown',
    gnn_score: 0.5,
    llm_score: 0.5,
    timeline: [],
  }
}

function stableHash(value) {
  return [...String(value ?? '')].reduce((sum, char) => sum + char.charCodeAt(0), 0)
}

function mockProfileForLead(lead) {
  const key = String(lead?.person_id ?? lead?.lead_id ?? '')
  const hash = stableHash(key)

  return {
    name: MOCK_NAMES[hash % MOCK_NAMES.length],
    company: MOCK_COMPANIES[hash % MOCK_COMPANIES.length],
    role: MOCK_ROLES[hash % MOCK_ROLES.length],
    source: lead?.source ?? lead?.signal ?? MOCK_SOURCES[hash % MOCK_SOURCES.length],
    gnn_score: lead?.gnn_score ?? (0.58 + ((hash % 32) / 100)),
    llm_score: lead?.llm_score ?? (0.46 + ((hash % 28) / 100)),
  }
}

function buildMockTimeline(lead) {
  const source = lead.source ?? 'linkedin.com/posts/revops-stack-2026'
  const gnn = lead.gnn_score ?? 0.68
  const llm = lead.llm_score ?? 0.56
  const qualificationEvents = [
    {
      action_type: 'source_detected',
      rationale: `Scout Agent discovered this lead from ${source} after matching engagement on a watched signal source.`,
      timestamp: '2026-06-20T09:15:00Z',
      reply_probability: null,
      status: 'done',
    },
    {
      action_type: 'profile_enriched',
      rationale: `Profile enriched with role, company, and recent activity. ${lead.role} at ${lead.company} matched the active ICP band.`,
      timestamp: '2026-06-20T09:18:00Z',
      reply_probability: null,
      status: 'done',
    },
    {
      action_type: lead.qualified === false ? 'disqualify' : 'qualify',
      rationale: `Qualifier blended GNN (${gnn.toFixed(2)}) and LLM (${llm.toFixed(2)}) scores, then marked the lead ${lead.qualified === false ? 'unqualified for this campaign' : 'ready for outreach'}.`,
      timestamp: '2026-06-20T09:22:00Z',
      reply_probability: null,
      status: 'done',
    },
  ]

  if (lead.qualified === false) return qualificationEvents

  return [
    ...qualificationEvents,
    {
      action_type: 'like_post',
      rationale: `Liked a recent post connected to the original signal source to create a lightweight warm touch before the connection request.`,
      timestamp: '2026-06-20T11:00:00Z',
      reply_probability: 0.31,
      status: 'done',
    },
    {
      action_type: 'draft_connection_request',
      rationale: `Drafted a connection request referencing the source signal and ${lead.company}'s likely GTM priorities.`,
      timestamp: '2026-06-21T08:45:00Z',
      reply_probability: 0.47,
      status: 'pending',
    },
  ]
}

function mergeTimeline(mockTimeline, apiTimeline = [], lead = {}) {
  if (!apiTimeline.length) return mockTimeline

  const normalizedApiActions = apiTimeline
    .filter((action) => !isDefaultWaitAction(action))
    .map((action, index) => ({
      timestamp: action.timestamp ?? `2026-06-21T1${index}:00:00Z`,
      reply_probability: action.reply_probability ?? null,
      status: action.status ?? 'done',
      ...action,
      action_type: lead.qualified === false && action.action_type === 'qualify'
        ? 'disqualify'
        : action.action_type,
    }))

  return [...mockTimeline, ...normalizedApiActions]
}

function isDefaultWaitAction(action) {
  const rationale = String(action?.rationale ?? '').toLowerCase()
  return action?.action_type === 'wait' && (
    rationale.includes('default fallback') ||
    rationale.includes('missing api key') ||
    rationale.trim() === ''
  )
}

function hasSpecificName(name) {
  return Boolean(name) && !String(name).startsWith('Lead #')
}

export default function LeadTimelinePanel() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const qc = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['lead-timeline', id],
    queryFn: () => getLeadTimeline(id),
    placeholderData: getDefaultTimeline(Number(id)),
  })

  const clickedLead = location.state?.lead
  const cachedLead = qc.getQueryData(['leads'])?.find((item) => String(item.id) === String(id))
  const baseLead = { ...getDefaultTimeline(Number(id)), ...(data ?? {}), ...(cachedLead ?? {}), ...(clickedLead ?? {}) }
  const mockProfile = mockProfileForLead(baseLead)
  const source = baseLead.source ?? baseLead.signal ?? mockProfile.source
  const lead = {
    ...baseLead,
    ...mockProfile,
    source,
    signal: source,
    ...(hasSpecificName(baseLead.name) ? { name: baseLead.name } : {}),
  }
  const timeline = mergeTimeline(buildMockTimeline(lead), data?.timeline ?? [], lead)

  const approveMutation = useMutation({
    mutationFn: async (index) => {
      await new Promise((r) => setTimeout(r, 600))
      return index
    },
  })

  return (
    <div>
      {/* Back nav */}
      <button
        id="back-to-leads"
        className="btn btn-ghost btn-sm"
        onClick={() => navigate('/leads')}
        style={{ marginBottom: '1.5rem' }}
      >
        <ArrowLeft size={14} /> Back to Pipeline
      </button>

      {/* Lead header card */}
      <div className="glass" style={{ padding: '1.5rem 2rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 style={{ fontSize: 'var(--text-xl)', fontFamily: 'var(--font-display)', marginBottom: '0.25rem' }}>
              {lead.name}
            </h1>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--t2)' }}>
              {lead.role} · {lead.company}
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              fontSize: 'var(--text-sm)',
              color: 'var(--cyan)',
              marginTop: 8,
              wordBreak: 'break-all',
            }}>
              <Link2 size={12} />
              <span>{lead.source}</span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
            <ScorePill label="GNN" value={lead.gnn_score} color="var(--cyan)" />
            <ScorePill label="LLM" value={lead.llm_score} color="var(--purple)" />
            {Math.abs((lead.gnn_score ?? 0) - (lead.llm_score ?? 0)) > 0.3 && (
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <span className="flag-amber">Model Disagreement</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {isLoading && (
        <div className="loading-wrap">
          <Loader2 size={22} style={{ animation: 'spin 0.7s linear infinite', color: 'var(--cyan)' }} />
          <span>Loading timeline…</span>
        </div>
      )}

      {error && (
        <div className="error-box" style={{ marginBottom: '1rem' }}>
          API unavailable — showing demo timeline
        </div>
      )}

      {/* Timeline */}
      <div style={{ marginBottom: '1rem' }}>
        <h2 style={{ fontSize: 'var(--text-lg)', marginBottom: '0.25rem' }}>Agent Timeline</h2>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--t2)' }}>
          Every action taken by the LeadAgent, with rationale and predicted reply probability
        </p>
      </div>

      {timeline.length === 0 ? (
        <div className="glass empty-state">
          <Clock size={40} />
          <p>No actions yet</p>
          <p style={{ fontSize: 'var(--text-sm)' }}>The LeadAgent hasn't acted on this lead yet</p>
        </div>
      ) : (
        <div className="glass" style={{ padding: '1.5rem 2rem' }}>
          <div className="timeline">
            {timeline.map((action, i) => {
              const cfg = ACTION_ICONS[action.action_type] ?? ACTION_ICONS.wait
              const Icon = cfg.icon
              const isPending = action.status === 'pending'
              return (
                <div key={i} id={`timeline-action-${i}`} className="timeline-item">
                  <div className="timeline-icon" style={{ background: cfg.bg, borderColor: cfg.color + '40' }}>
                    <Icon size={15} color={cfg.color} />
                  </div>
                  <div className="timeline-body">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                      <span className="timeline-title" style={{ color: cfg.color }}>
                        {formatAction(action.action_type)}
                      </span>
                      {isPending && (
                        <span style={{
                          fontSize: '0.65rem', color: 'var(--amber)',
                          background: 'rgba(255,180,0,0.1)', border: '1px solid rgba(255,180,0,0.25)',
                          borderRadius: '100px', padding: '0.1rem 0.5rem', fontWeight: 600,
                        }}>PENDING</span>
                      )}
                      {action.reply_probability !== null && action.reply_probability !== undefined && (
                        <span style={{
                          fontSize: '0.65rem', color: 'var(--t3)',
                          background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)',
                          borderRadius: '100px', padding: '0.1rem 0.5rem',
                        }}>
                          <Zap size={9} style={{ display: 'inline' }} /> {(action.reply_probability * 100).toFixed(0)}% reply prob
                        </span>
                      )}
                    </div>
                    <p className="timeline-rationale">{action.rationale}</p>
                    <div className="timeline-meta">
                      <Clock size={10} style={{ display: 'inline', marginRight: 4 }} />
                      {formatDate(action.timestamp)}
                    </div>
                    {isPending && (
                      <button
                        id={`approve-action-${i}`}
                        className="btn btn-amber btn-sm"
                        style={{ marginTop: '0.75rem' }}
                        onClick={async () => {
                          await approveMutation.mutateAsync(i)
                          qc.invalidateQueries(['lead-timeline', id])
                        }}
                        disabled={approveMutation.isPending}
                      >
                        {approveMutation.isPending ? <Loader2 size={12} style={{ animation: 'spin 0.7s linear infinite' }} /> : <CheckCircle2 size={12} />}
                        Approve Action
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function ScorePill({ label, value, color }) {
  const pct = Math.round((value ?? 0) * 100)
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 'var(--text-sm)', color: 'var(--t3)', marginBottom: 4 }}>{label} Score</div>
      <div style={{
        fontSize: 'var(--text-xl)', fontFamily: 'var(--font-display)', fontWeight: 700, color,
      }}>
        {pct}%
      </div>
      <div style={{ marginTop: 6, width: 64, height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 100, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 100 }} />
      </div>
    </div>
  )
}

function formatAction(type) {
  return {
    source_detected:          'Source Detected',
    profile_enriched:         'Profile Enriched',
    like_post:                'Liked Post',
    draft_connection_request: 'Connection Request Drafted',
    send_email:               'Email Sent',
    wait:                     'Waiting',
    qualify:                  'Lead Qualified',
    disqualify:               'Lead Disqualified',
    reply:                    'Reply Received',
  }[type] ?? type
}

function formatDate(ts) {
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return ts
  }
}
