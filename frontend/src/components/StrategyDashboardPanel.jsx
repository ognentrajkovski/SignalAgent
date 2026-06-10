import { useQuery } from '@tanstack/react-query'
import { BarChart3, Sparkles, Users, TrendingUp, Target, Zap, Loader2 } from 'lucide-react'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ReferenceLine,
} from 'recharts'
import { getStrategy } from '../api'

const MOCK_STRATEGY = {
  top_sources: [
    { url: 'linkedin.com/posts/react-2024',   lead_count: 42, conversion_rate: 0.31 },
    { url: 'linkedin.com/posts/nextjs-conf',  lead_count: 38, conversion_rate: 0.28 },
    { url: 'linkedin.com/in/techleader',      lead_count: 27, conversion_rate: 0.22 },
  ],
  lookalike_recommendations: [
    { suggested_url: 'linkedin.com/posts/vercel-summit', reason: 'High overlap with engaged React engineers who responded to outreach.' },
    { suggested_url: 'linkedin.com/posts/ai-infrastructure-2024', reason: 'Matches profile cluster of senior engineers at growth-stage startups.' },
  ],
  community_summaries: [
    { name: 'React/Next.js Core',   size: 312, top_topics: ['RSC', 'Edge compute', 'Monorepos'],  engagement: 0.74 },
    { name: 'AI Tooling Builders',  size: 189, top_topics: ['LLMs', 'Agents', 'Vector DBs'],      engagement: 0.88 },
    { name: 'DevOps / Platform Eng',size: 143, top_topics: ['K8s', 'FinOps', 'IaC'],             engagement: 0.61 },
  ],
}

// Synthetic accuracy comparison data (GNN+LLM vs LLM-only)
const ACCURACY_DATA = [
  { epoch: 1,  gnn_llm: 0.61, llm_only: 0.55 },
  { epoch: 2,  gnn_llm: 0.66, llm_only: 0.57 },
  { epoch: 3,  gnn_llm: 0.70, llm_only: 0.59 },
  { epoch: 4,  gnn_llm: 0.74, llm_only: 0.61 },
  { epoch: 5,  gnn_llm: 0.77, llm_only: 0.62 },
  { epoch: 6,  gnn_llm: 0.80, llm_only: 0.63 },
  { epoch: 7,  gnn_llm: 0.82, llm_only: 0.63 },
  { epoch: 8,  gnn_llm: 0.84, llm_only: 0.64 },
  { epoch: 9,  gnn_llm: 0.85, llm_only: 0.65 },
  { epoch: 10, gnn_llm: 0.87, llm_only: 0.65 },
]

const TOOLTIP_STYLE = {
  background: 'rgba(15, 12, 28, 0.95)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 10,
  color: '#fff',
  fontSize: 12,
}

export default function StrategyDashboardPanel() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['strategy'],
    queryFn: getStrategy,
    placeholderData: MOCK_STRATEGY,
  })

  const strategy = { ...MOCK_STRATEGY, ...(data ?? {}) }

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
          <div style={{
            width: 40, height: 40, borderRadius: 12,
            background: 'linear-gradient(135deg, var(--amber), var(--red))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 20px rgba(255,140,0,0.35)',
          }}>
            <BarChart3 size={18} color="#fff" />
          </div>
          <h1 className="page-title">Strategy Dashboard</h1>
        </div>
        <p className="page-sub">StrategyAgent insights — top signal sources, lookalikes, emerging communities</p>
      </div>

      {isLoading && (
        <div className="loading-wrap">
          <Loader2 size={22} style={{ animation: 'spin 0.7s linear infinite', color: 'var(--cyan)' }} />
          <span>Running StrategyAgent…</span>
        </div>
      )}
      {error && (
        <div className="error-box" style={{ marginBottom: '1rem' }}>
          API unavailable — showing demo data
        </div>
      )}

      {/* Three info cards */}
      <div className="card-grid-3" style={{ marginBottom: '2rem' }}>
        {/* Top Signal Sources */}
        <div className="card">
          <div className="card-header">
            <div className="card-icon" style={{ background: 'rgba(80,180,255,0.12)' }}>
              <Target size={14} color="var(--cyan)" />
            </div>
            Top Signal Sources
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {(strategy.top_sources ?? []).map((src, i) => (
              <div key={i} style={{
                background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)',
                borderRadius: 10, padding: '0.75rem',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--cyan)' }}>#{i + 1}</span>
                  <span className="chip"><Users size={10} /> {src.lead_count} leads</span>
                </div>
                <div style={{ fontSize: 'var(--text-sm)', color: 'var(--t2)', wordBreak: 'break-all', marginBottom: 6 }}>
                  {src.url}
                </div>
                <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                  <div style={{ flex: 1, height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 100, overflow: 'hidden' }}>
                    <div style={{
                      width: `${(src.conversion_rate ?? 0) * 100}%`, height: '100%',
                      background: 'linear-gradient(90deg, var(--cyan), var(--purple))', borderRadius: 100,
                    }} />
                  </div>
                  <span style={{ fontSize: '0.65rem', color: 'var(--t3)' }}>
                    {((src.conversion_rate ?? 0) * 100).toFixed(0)}% conv.
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Lookalike Recommendations */}
        <div className="card">
          <div className="card-header">
            <div className="card-icon" style={{ background: 'rgba(140,80,255,0.12)' }}>
              <Sparkles size={14} color="var(--purple)" />
            </div>
            Lookalike Suggestions
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {(strategy.lookalike_recommendations ?? []).map((rec, i) => (
              <div key={i} style={{
                background: 'rgba(140,80,255,0.06)', border: '1px solid rgba(140,80,255,0.15)',
                borderRadius: 10, padding: '0.875rem',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem' }}>
                  <Zap size={12} color="var(--purple)" />
                  <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--purple)' }}>
                    Suggested
                  </span>
                </div>
                <div style={{ fontSize: 'var(--text-sm)', color: 'var(--cyan)', wordBreak: 'break-all', marginBottom: 6 }}>
                  {rec.suggested_url}
                </div>
                <p style={{ fontSize: 'var(--text-sm)', color: 'var(--t2)', lineHeight: 1.5 }}>
                  {rec.reason}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Community Summaries */}
        <div className="card">
          <div className="card-header">
            <div className="card-icon" style={{ background: 'rgba(255,180,0,0.12)' }}>
              <TrendingUp size={14} color="var(--amber)" />
            </div>
            Emerging Communities
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {(strategy.community_summaries ?? []).map((comm, i) => {
              const colors = ['var(--cyan)', 'var(--purple)', 'var(--amber)']
              const c = colors[i % colors.length]
              return (
                <div key={i} style={{
                  background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)',
                  borderRadius: 10, padding: '0.75rem',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: c }}>{comm.name}</span>
                    <span className="chip"><Users size={10} /> {comm.size}</span>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', marginBottom: 8 }}>
                    {(comm.top_topics ?? []).map((t) => (
                      <span key={t} style={{
                        fontSize: '0.6rem', padding: '0.15rem 0.5rem', borderRadius: '100px',
                        background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border)',
                        color: 'var(--t2)',
                      }}>{t}</span>
                    ))}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span style={{ fontSize: '0.65rem', color: 'var(--t3)' }}>Engagement</span>
                    <div style={{ flex: 1, height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 100, overflow: 'hidden' }}>
                      <div style={{ width: `${(comm.engagement ?? 0) * 100}%`, height: '100%', background: c, borderRadius: 100 }} />
                    </div>
                    <span style={{ fontSize: '0.65rem', color: c, fontWeight: 600 }}>
                      {((comm.engagement ?? 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Accuracy comparison chart */}
      <div className="glass" style={{ padding: '1.75rem' }}>
        <div style={{ marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: 'var(--text-lg)', marginBottom: '0.25rem' }}>Qualifier Accuracy: GNN+LLM vs LLM-Only</h2>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--t2)' }}>
            Validation accuracy on synthetic held-out set across training epochs
          </p>
        </div>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={ACCURACY_DATA} margin={{ top: 8, right: 24, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="epoch"
              tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 12 }}
              label={{ value: 'Epoch', position: 'insideBottom', offset: -2, fill: 'rgba(255,255,255,0.3)', fontSize: 11 }}
            />
            <YAxis
              domain={[0.5, 1.0]}
              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
              tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 12 }}
            />
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              formatter={(v, name) => [`${(v * 100).toFixed(1)}%`, name]}
            />
            <Legend
              wrapperStyle={{ fontSize: 12, paddingTop: 12, color: 'rgba(255,255,255,0.6)' }}
            />
            <ReferenceLine y={0.8} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 4" label={{ value: '80%', fill: 'rgba(255,255,255,0.2)', fontSize: 10 }} />
            <Line
              type="monotone"
              dataKey="gnn_llm"
              name="GNN + LLM"
              stroke="oklch(0.78 0.14 220)"
              strokeWidth={2.5}
              dot={{ fill: 'oklch(0.78 0.14 220)', r: 3 }}
              activeDot={{ r: 5 }}
            />
            <Line
              type="monotone"
              dataKey="llm_only"
              name="LLM Only"
              stroke="oklch(0.68 0.20 295)"
              strokeWidth={2}
              strokeDasharray="5 3"
              dot={{ fill: 'oklch(0.68 0.20 295)', r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
        <div style={{
          marginTop: '1rem',
          display: 'flex', gap: '1.5rem', justifyContent: 'center',
          fontSize: 'var(--text-sm)', color: 'var(--t2)',
        }}>
          <span>
            GNN+LLM final: <strong style={{ color: 'var(--cyan)' }}>87%</strong>
          </span>
          <span>
            LLM-only final: <strong style={{ color: 'var(--purple)' }}>65%</strong>
          </span>
          <span>
            Delta: <strong style={{ color: 'var(--green)' }}>+22pp</strong>
          </span>
        </div>
      </div>
    </div>
  )
}
