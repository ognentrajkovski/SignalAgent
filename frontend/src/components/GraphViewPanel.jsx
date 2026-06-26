import { useRef, useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import CytoscapeComponent from 'react-cytoscapejs'
import { GitBranch, ZoomIn, ZoomOut, Maximize2, Info, Loader2 } from 'lucide-react'
import { getGraphData } from '../api'

// Community metadata aligned with backend COMMUNITY_ARCHETYPES order
const COMMUNITIES = [
  { name: 'RevOps Leaders',  border: '#50b4ff', bg: 'rgba(80,180,255,0.15)',  dot: 'rgba(80,180,255,0.85)'  },
  { name: 'PLG Founders',    border: '#8c50ff', bg: 'rgba(140,80,255,0.15)', dot: 'rgba(140,80,255,0.85)' },
  { name: 'GTM Executives',  border: '#ffb400', bg: 'rgba(255,180,0,0.15)',  dot: 'rgba(255,180,0,0.85)'  },
]

function buildElements(nodes, edges) {
  const cyNodes = nodes.map((n) => ({
    data: {
      id: n.id,
      label: n.label,
      nodeType: n.type,
      full_name: n.full_name ?? n.label,
      role: n.role ?? '',
      company: n.company ?? '',
      community: n.community_id ?? 0,
      qualified: n.qualified ?? false,
      gnn_score: n.gnn_score ?? 0,
      llm_score: n.llm_score ?? 0,
      disagreement_flag: n.disagreement_flag ?? false,
      source_url: n.source_url ?? '',
      lead_id: n.lead_id ?? null,
    },
  }))

  const cyEdges = edges.map((e) => ({
    data: {
      id: e.id,
      source: e.source,
      target: e.target,
      rel: e.type,
    },
  }))

  return [...cyNodes, ...cyEdges]
}

const CYTO_STYLE = [
  {
    selector: 'node[nodeType = "person"]',
    style: {
      width: 38, height: 38,
      label: 'data(label)',
      'font-size': 9,
      'font-family': 'Inter, sans-serif',
      'text-valign': 'bottom',
      'text-margin-y': 4,
      'text-outline-width': 2,
      'text-outline-color': '#0d0b1a',
      color: 'rgba(255,255,255,0.7)',
      'border-width': 2,
      'border-color': 'rgba(255,255,255,0.15)',
      'background-color': '#444',
      'transition-property': 'background-color border-color width height',
      'transition-duration': '0.2s',
    },
  },
  {
    selector: 'node[nodeType = "person"][?qualified]',
    style: { 'border-width': 2.5 },
  },
  {
    selector: 'node[nodeType = "person"][!qualified]',
    style: {
      'background-color': 'rgba(100,100,120,0.6)',
      'border-color': 'rgba(255,255,255,0.1)',
      opacity: 0.6,
    },
  },
  {
    selector: 'node[nodeType = "person"][community = 0]',
    style: { 'border-color': '#50b4ff', 'background-color': 'rgba(80,180,255,0.25)' },
  },
  {
    selector: 'node[nodeType = "person"][community = 1]',
    style: { 'border-color': '#8c50ff', 'background-color': 'rgba(140,80,255,0.25)' },
  },
  {
    selector: 'node[nodeType = "person"][community = 2]',
    style: { 'border-color': '#ffb400', 'background-color': 'rgba(255,180,0,0.25)' },
  },
  {
    selector: 'node[nodeType = "source"]',
    style: {
      shape: 'round-rectangle',
      width: 48, height: 22,
      'background-color': 'rgba(255,180,0,0.15)',
      'border-color': 'rgba(255,180,0,0.45)',
      'border-width': 1.5,
      label: 'data(label)',
      'font-size': 8,
      color: 'rgba(255,180,0,0.9)',
      'text-valign': 'center',
      'text-outline-width': 0,
    },
  },
  {
    selector: 'node:selected',
    style: { 'border-color': '#fff', 'border-width': 3, width: 46, height: 46 },
  },
  {
    selector: 'edge',
    style: {
      width: 1,
      'line-color': 'rgba(255,255,255,0.07)',
      'curve-style': 'bezier',
      'target-arrow-shape': 'none',
    },
  },
  {
    selector: 'edge[rel = "engaged_with"]',
    style: {
      'line-color': 'rgba(255,180,0,0.25)',
      'line-style': 'dashed',
      'line-dash-pattern': [4, 3],
    },
  },
  {
    selector: 'edge[rel = "co_engaged"]',
    style: { 'line-color': 'rgba(255,255,255,0.06)' },
  },
]

export default function GraphViewPanel() {
  const navigate = useNavigate()
  const cyRef = useRef(null)
  const [selected, setSelected] = useState(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['graph'],
    queryFn: getGraphData,
  })

  const nodes = data?.nodes ?? []
  const edges = data?.edges ?? []
  const elements = buildElements(nodes, edges)

  const personNodes   = nodes.filter((n) => n.type === 'person')
  const sourceNodes   = nodes.filter((n) => n.type === 'source')
  const qualifiedCount = personNodes.filter((n) => n.qualified).length

  const handleCyInit = useCallback((cy) => {
    cyRef.current = cy
    cy.on('tap', 'node', (evt) => setSelected(evt.target.data()))
    cy.on('tap', (evt) => { if (evt.target === cy) setSelected(null) })
  }, [])

  const zoom = (dir) => {
    const cy = cyRef.current
    if (!cy) return
    const curr = cy.zoom()
    cy.zoom({ level: dir === 'in' ? curr * 1.3 : curr / 1.3, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } })
  }

  const communityOf = (id) => COMMUNITIES[id % COMMUNITIES.length] ?? COMMUNITIES[0]

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
          <div style={{
            width: 40, height: 40, borderRadius: 12,
            background: 'linear-gradient(135deg, var(--green), var(--cyan))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 20px rgba(0,220,120,0.3)',
          }}>
            <GitBranch size={18} color="#fff" />
          </div>
          <h1 className="page-title">Graph View</h1>
        </div>
        <p className="page-sub">Live engagement graph — pipeline leads, source signals, and community clusters</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        <StatCard label="Pipeline leads" value={personNodes.length} color="var(--cyan)" />
        <StatCard label="Qualified"      value={qualifiedCount}    color="var(--green)" />
        <StatCard label="Signal sources" value={sourceNodes.length} color="var(--amber)" />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <LegendItem color="rgba(80,180,255,0.8)" label="Qualified lead" />
          <LegendItem color="rgba(100,100,120,0.8)" label="Unqualified" />
          <LegendItem color="rgba(255,180,0,0.6)" label="Signal source" shape="square" />
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <div style={{ width: 22, height: 2, borderTop: '2px dashed rgba(255,180,0,0.4)' }} />
            <span style={{ fontSize: 'var(--text-sm)', color: 'var(--t3)' }}>Engagement</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button id="graph-zoom-in"  className="btn btn-ghost btn-sm" onClick={() => zoom('in')}>  <ZoomIn  size={13} /></button>
          <button id="graph-zoom-out" className="btn btn-ghost btn-sm" onClick={() => zoom('out')}> <ZoomOut size={13} /></button>
          <button id="graph-fit"      className="btn btn-ghost btn-sm" onClick={() => cyRef.current?.fit(undefined, 40)}><Maximize2 size={13} /></button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 260px' : '1fr', gap: '1rem', transition: 'grid-template-columns 0.25s ease' }}>
        <div className="graph-container" style={{ position: 'relative' }}>
          {isLoading && (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem', color: 'var(--t2)', zIndex: 10 }}>
              <Loader2 size={20} style={{ animation: 'spin 0.7s linear infinite', color: 'var(--cyan)' }} />
              <span>Loading graph...</span>
            </div>
          )}

          {error && (
            <div className="error-box" style={{ margin: '1rem' }}>Failed to load graph — check the backend is running</div>
          )}

          {!isLoading && !error && elements.length === 0 && (
            <div className="glass empty-state" style={{ margin: '2rem' }}>
              <GitBranch size={40} />
              <p style={{ fontSize: 'var(--text-lg)', color: 'var(--t2)' }}>No leads in the graph yet</p>
              <p style={{ fontSize: 'var(--text-sm)' }}>Add a signal source to start discovering leads</p>
            </div>
          )}

          {elements.length > 0 && (
            <CytoscapeComponent
              key={elements.length}
              elements={elements}
              style={{ width: '100%', height: '100%' }}
              stylesheet={CYTO_STYLE}
              layout={{
                name: 'cose',
                animate: true,
                animationDuration: 800,
                nodeRepulsion: () => 8000,
                idealEdgeLength: () => 80,
                gravity: 0.4,
                randomize: false,
              }}
              cy={handleCyInit}
            />
          )}
        </div>

        {selected && (
          <div className="glass" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', alignSelf: 'start' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--t3)', fontSize: 'var(--text-sm)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              <Info size={12} /> Node Detail
            </div>

            <div style={{ borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem' }}>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 'var(--text-lg)', marginBottom: 4 }}>
                {selected.nodeType === 'person' ? (selected.full_name || selected.label) : selected.label}
              </div>
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--t3)' }}>{selected.id}</div>
            </div>

            {selected.nodeType === 'person' && (
              <>
                {selected.role    && <InfoRow label="Role"    value={selected.role}    />}
                {selected.company && <InfoRow label="Company" value={selected.company} />}
                <InfoRow
                  label="Status"
                  value={selected.qualified ? 'Qualified' : 'Unqualified'}
                  color={selected.qualified ? 'var(--green)' : 'var(--t3)'}
                />
                <InfoRow label="GNN Score" value={`${(selected.gnn_score * 100).toFixed(0)}%`}  color="var(--cyan)"   />
                <InfoRow label="LLM Score" value={`${(selected.llm_score * 100).toFixed(0)}%`}  color="var(--purple)" />
                {selected.disagreement_flag && (
                  <span className="flag-amber" style={{ alignSelf: 'flex-start' }}>Model Disagreement</span>
                )}
                <InfoRow
                  label="Community"
                  value={communityOf(selected.community).name}
                  color={communityOf(selected.community).dot}
                />
                {selected.lead_id && (
                  <button
                    id={`view-timeline-${selected.id}`}
                    className="btn btn-primary"
                    style={{ marginTop: '0.5rem' }}
                    onClick={() => navigate(`/leads/${selected.lead_id}`)}
                  >
                    View Timeline
                  </button>
                )}
              </>
            )}

            {selected.nodeType === 'source' && (
              <>
                <InfoRow label="Type" value="Signal Source" color="var(--amber)" />
                <div style={{ fontSize: 'var(--text-sm)', color: 'var(--t3)', wordBreak: 'break-all' }}>
                  {selected.source_url}
                </div>
              </>
            )}

            <button className="btn btn-ghost btn-sm" onClick={() => setSelected(null)} style={{ marginTop: 'auto' }}>
              Close
            </button>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem', flexWrap: 'wrap' }}>
        {COMMUNITIES.map(({ name, bg, dot, border }) => (
          <div key={name} style={{
            display: 'flex', alignItems: 'center', gap: '0.4rem',
            padding: '0.3rem 0.75rem',
            background: bg,
            borderRadius: '100px',
            border: `1px solid ${border}55`,
            fontSize: 'var(--text-sm)', color: 'var(--t2)',
          }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: dot }} />
            {name}
          </div>
        ))}
      </div>
    </div>
  )
}

function LegendItem({ color, label, shape }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
      <div style={{ width: 12, height: 12, borderRadius: shape === 'square' ? 2 : '50%', background: color }} />
      <span style={{ fontSize: 'var(--text-sm)', color: 'var(--t3)' }}>{label}</span>
    </div>
  )
}

function InfoRow({ label, value, color }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-sm)', alignItems: 'center' }}>
      <span style={{ color: 'var(--t3)' }}>{label}</span>
      <span style={{ color: color ?? 'var(--t1)', fontWeight: 500 }}>{value}</span>
    </div>
  )
}

function StatCard({ label, value, color }) {
  return (
    <div className="glass" style={{ padding: '1rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
      <div style={{ fontSize: 'var(--text-sm)', color: 'var(--t3)' }}>{label}</div>
      <div style={{ fontSize: 'var(--text-2xl)', fontFamily: 'var(--font-display)', fontWeight: 700, color }}>{value}</div>
    </div>
  )
}
