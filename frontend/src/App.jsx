import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import {
  Radio,
  Users,
  BarChart3,
  GitBranch,
  Cpu,
  ChevronRight,
  Activity,
} from 'lucide-react'
import SignalSourcesPanel from './components/SignalSourcesPanel'
import LeadPipelinePanel from './components/LeadPipelinePanel'
import LeadTimelinePanel from './components/LeadTimelinePanel'
import StrategyDashboardPanel from './components/StrategyDashboardPanel'
import GraphViewPanel from './components/GraphViewPanel'

const NAV = [
  { to: '/',          icon: Radio,      label: 'Signal Sources' },
  { to: '/leads',     icon: Users,      label: 'Lead Pipeline'  },
  { to: '/strategy',  icon: BarChart3,  label: 'Strategy'       },
  { to: '/graph',     icon: GitBranch,  label: 'Graph View'     },
]

function Sidebar() {
  const location = useLocation()

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="brand-icon">
          <Cpu size={18} />
        </div>
        <div>
          <div className="brand-name">SignalAgent</div>
          <div className="brand-sub">GTM Intelligence</div>
        </div>
      </div>

      {/* Status pulse */}
      <div className="sidebar-status">
        <Activity size={12} className="pulse-icon" />
        <span>Pipeline active</span>
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        {NAV.map(({ to, icon: Icon, label }) => {
          const active =
            to === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(to)
          return (
            <NavLink key={to} to={to} className={`nav-item ${active ? 'active' : ''}`}>
              <Icon size={16} />
              <span>{label}</span>
              {active && <ChevronRight size={14} className="nav-chevron" />}
            </NavLink>
          )
        })}
      </nav>
    </aside>
  )
}

export default function App() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/"              element={<SignalSourcesPanel />} />
          <Route path="/leads"         element={<LeadPipelinePanel />} />
          <Route path="/leads/:id"     element={<LeadTimelinePanel />} />
          <Route path="/strategy"      element={<StrategyDashboardPanel />} />
          <Route path="/graph"         element={<GraphViewPanel />} />
        </Routes>
      </main>
    </div>
  )
}
