import { useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import CytoscapeComponent from 'react-cytoscapejs'
import { GitBranch, ZoomIn, ZoomOut, Maximize2, Info } from 'lucide-react'

// Synthetic graph data for demonstration
const GRAPH_NODES = [
  // Qualified (blue) leads
  { id: 'p_001', label: 'Alex C.', qualified: true,  community: 0, score: 0.91 },
  { id: 'p_002', label: 'Maya P.', qualified: true,  community: 0, score: 0.87 },
  { id: 'p_004', label: 'Sam R.',  qualified: true,  community: 1, score: 0.95 },
  { id: 'p_006', label: 'Chris M.',qualified: true,  community: 1, score: 0.72 },
  { id: 'p_007', label: 'Priya L.',qualified: true,  community: 2, score: 0.83 },
  { id: 'p_008', label: 'Tom W.',  qualified: true,  community: 0, score: 0.79 },
  { id: 'p_009', label: 'Nina S.', qualified: true,  community: 2, score: 0.88 },
  // Unqualified (grey)
  { id: 'p_003', label: 'Jordan K.',qualified: false, community: 0, score: 0.44 },
  { id: 'p_005', label: 'Dana W.', qualified: false, community: 1, score: 0.29 },
  { id: 'p_010', label: 'Lee B.',  qualified: false, community: 2, score: 0.35 },
  { id: 'p_011', label: 'Mo T.',   qualified: false, community: 1, score: 0.41 },
  { id: 'p_012', label: 'Rae N.',  qualified: false, community: 2, score: 0.38 },
  // Posts
  { id: 'post_1', label: 'React Post',   type: 'post', community: 0 },
  { id: 'post_2', label: 'Next.js Conf', type: 'post', community: 0 },
  { id: 'post_3', label: 'Linear Launch',type: 'post', community: 1 },
]

const GRAPH_EDGES = [
  { source: 'p_001', target: 'post_1', rel: 'ENGAGED' },
  { source: 'p_002', target: 'post_2', rel: 'ENGAGED' },
  { source: 'p_003', target: 'post_1', rel: 'ENGAGED' },
  { source: 'p_004', target: 'post_3', rel: 'ENGAGED' },
  { source: 'p_006', target: 'post_3', rel: 'ENGAGED' },
  { source: 'p_008', target: 'post_1', rel: 'ENGAGED' },
  { source: 'p_011', target: 'post_3', rel: 'ENGAGED' },
  { source: 'p_001', target: 'p_002', rel: 'CONNECTED' },
  { source: 'p_001', target: 'p_008', rel: 'CONNECTED' },
  { source: 'p_002', target: 'p_003', rel: 'CONNECTED' },
  { source: 'p_004', target: 'p_006', rel: 'CONNECTED' },
  { source: 'p_004', target: 'p_011', rel: 'CONNECTED' },
  { source: 'p_005', target: 'p_011', rel: 'CONNECTED' },
  { source: 'p_007', target: 'p_009', rel: 'CONNECTED' },
  { source: 'p_007', target: 'p_010', rel: 'CONNECTED' },
  { source: 'p_009', target: 'p_012', rel: 'CONNECTED' },
]

// Community tint colors (semi-transparent backgrounds)
const COMMUNITY_COLORS = [
  'rgba(80,180,255,0.18)',   // 0: cyan
  'rgba(140,80,255,0.18)',   // 1: purple
  'rgba(255,180,0,0.15)',    // 2: amber
]

const LEAD_ID_MAP = {
  p_001: 1, p_002: 2, p_003: 3, p_004: 4,
  p_005: 5, p_006: 6, p_007: 7, p_008: 8,
}

function buildElements() {
  const nodes = GRAPH_NODES.map((n) => ({
    data: {
      id: n.id,
      label: n.label,
      nodeType: n.type ?? 'person',
      qualified: n.qualified ?? false,
      community: n.community ?? 0,
      score: n.score ?? 0,
    },
  }))
  const edges = GRAPH_EDGES.map((e, i) => ({
    data: { id: `e${i}`, source: e.source, target: e.target, rel: e.rel },
  }))
  return [...nodes, ...edges]
}

const CYTO_STYLE = [
  {
    selector: 'node[nodeType = "person"]',
    style: {
      width: 38, height: 38,
      label: 'data(label)',
      'font-size': 9, 'font-family': 'Inter, sans-serif',
      'text-valign': 'bottom', 'text-margin-y': 4,
      'text-outline-width': 2, 'text-outline-color': '#0d0b1a',
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
    style: {
      'background-color': 'oklch(0.55 0.18 230)',
      'border-color': 'oklch(0.78 0.14 220)',
      'border-width': 2.5,
    },
  },
  {
    selector: 'node[nodeType = "person"][!qualified]',
    style: {
      'background-color': 'rgba(100,100,120,0.6)',
      'border-color': 'rgba(255,255,255,0.1)',
    },
  },
  {
    selector: 'node[nodeType = "post"]',
    style: {
      shape: 'round-rectangle',
      width: 44, height: 22,
      'background-color': 'rgba(255,180,0,0.2)',
      'border-color': 'rgba(255,180,0,0.5)',
      'border-width': 1.5,
      label: 'data(label)',
      'font-size': 8, color: 'rgba(255,180,0,0.9)',
      'text-valign': 'center',
      'text-outline-width': 0,
    },
  },
  {
    selector: 'node:selected',
    style: {
      'border-color': '#fff',
      'border-width': 3,
      width: 46, height: 46,
    },
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
    selector: 'edge[rel = "ENGAGED"]',
    style: {
      'line-color': 'rgba(255,180,0,0.2)',
      'line-style': 'dashed',
      'line-dash-pattern': [4, 3],
    },
  },
]

export default function GraphViewPanel() {
  const navigate = useNavigate()
  const cyRef = useRef(null)
  const [selected, setSelected] = useState(null)
  const elements = buildElements()

  const handleCyInit = useCallback((cy) => {
    cyRef.current = cy
    cy.on('tap', 'node', (evt) => {
      const node = evt.target
      const data = node.data()
      setSelected(data)
    })
    cy.on('tap', (evt) => {
      if (evt.target === cy) setSelected(null)
    })
  }, [])

  const zoom = (dir) => {
    const cy = cyRef.current
    if (!cy) return
    const curr = cy.zoom()
    cy.zoom({ level: dir === 'in' ? curr * 1.3 : curr / 1.3, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } })
  }

  const fit = () => cyRef.current?.fit(undefined, 40)

  const openTimeline = () => {
    if (!selected) return
    const leadId = LEAD_ID_MAP[selected.id]
    if (leadId) navigate(`/leads/${leadId}`)
  }

  return (
    <div>
      {/* Header */}
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
        <p className="page-sub">Force-directed social graph — blue = qualified, grey = unqualified, communities shaded</p>
      </div>

      {/* Legend + Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <LegendItem color="oklch(0.55 0.18 230)" label="Qualified lead" />
          <LegendItem color="rgba(100,100,120,0.8)" label="Unqualified" />
          <LegendItem color="rgba(255,180,0,0.6)" label="Post node" shape="square" />
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <div style={{ width: 22, height: 2, borderTop: '2px dashed rgba(255,180,0,0.4)' }} />
            <span style={{ fontSize: 'var(--text-sm)', color: 'var(--t3)' }}>Engagement</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <div style={{ width: 22, height: 2, background: 'rgba(255,255,255,0.15)' }} />
            <span style={{ fontSize: 'var(--text-sm)', color: 'var(--t3)' }}>Connected</span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button id="graph-zoom-in"  className="btn btn-ghost btn-sm" onClick={() => zoom('in')}>  <ZoomIn  size={13} /></button>
          <button id="graph-zoom-out" className="btn btn-ghost btn-sm" onClick={() => zoom('out')}> <ZoomOut size={13} /></button>
          <button id="graph-fit"      className="btn btn-ghost btn-sm" onClick={fit}>               <Maximize2 size={13} /></button>
        </div>
      </div>

      {/* Graph + sidebar */}
      <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 260px' : '1fr', gap: '1rem', transition: 'all 0.3s ease' }}>
        <div className="graph-container">
          <CytoscapeComponent
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
        </div>

        {/* Node detail panel */}
        {selected && (
          <div className="glass" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', alignSelf: 'start' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--t3)', fontSize: 'var(--text-sm)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              <Info size={12} /> Node Detail
            </div>

            <div style={{ borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem' }}>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 'var(--text-lg)', marginBottom: 4 }}>
                {selected.label}
              </div>
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--t3)' }}>{selected.id}</div>
            </div>

            {selected.nodeType === 'person' && (
              <>
                <InfoRow label="Type" value={selected.qualified ? 'Qualified' : 'Unqualified'} color={selected.qualified ? 'var(--green)' : 'var(--t3)'} />
                <InfoRow label="GNN Score" value={`${(selected.score * 100).toFixed(0)}%`} color="var(--cyan)" />
                <InfoRow label="Community" value={`#${selected.community}`} color={COMMUNITY_COLORS[selected.community % 3].replace('0.18', '1').replace('0.15', '1')} />

                {LEAD_ID_MAP[selected.id] && (
                  <button
                    id={`view-timeline-${selected.id}`}
                    className="btn btn-primary"
                    style={{ marginTop: '0.5rem' }}
                    onClick={openTimeline}
                  >
                    View Timeline
                  </button>
                )}
              </>
            )}
            {selected.nodeType === 'post' && (
              <InfoRow label="Type" value="LinkedIn Post" color="var(--amber)" />
            )}

            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setSelected(null)}
              style={{ marginTop: 'auto' }}
            >
              Close
            </button>
          </div>
        )}
      </div>

      {/* Community color key */}
      <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem', flexWrap: 'wrap' }}>
        {['React/Next.js Core', 'AI Tooling Builders', 'DevOps / Platform Eng'].map((name, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: '0.4rem',
            padding: '0.3rem 0.75rem',
            background: COMMUNITY_COLORS[i],
            borderRadius: '100px',
            border: `1px solid ${COMMUNITY_COLORS[i].replace('0.18', '0.4').replace('0.15', '0.4')}`,
            fontSize: 'var(--text-sm)', color: 'var(--t2)',
          }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: COMMUNITY_COLORS[i].replace('0.18', '1').replace('0.15', '1') }} />
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
      <div style={{
        width: shape === 'square' ? 12 : 12,
        height: 12,
        borderRadius: shape === 'square' ? 2 : '50%',
        background: color,
      }} />
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
