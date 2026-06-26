import { useQuery } from '@tanstack/react-query'
import { BarChart3, Sparkles, Users, TrendingUp, Target, Zap, Loader2 } from 'lucide-react'

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
    { name: 'RevOps Leaders', size: 466, top_topics: ['Revenue operations stack', 'CRM hygiene', 'GTM alignment'], engagement: 0.74 },
    { name: 'PLG Founders',  size: 466, top_topics: ['Product-led growth', 'Freemium conversion', 'Self-serve onboarding'], engagement: 0.88 },
    { name: 'GTM Executives', size: 468, top_topics: ['Enterprise sales motion', 'Outbound strategy', 'Pipeline generation'], engagement: 0.61 },
  ],
}


export default function StrategyDashboardPanel() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['strategy'],
    queryFn: getStrategy,
    placeholderData: MOCK_STRATEGY,
  })

  const strategy = {
    ...MOCK_STRATEGY,
    ...(data ?? {}),
    top_sources: data?.top_sources ?? data?.top_performing_sources ?? MOCK_STRATEGY.top_sources,
  }

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
            Target Communities
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
    </div>
  )
}
