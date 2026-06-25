import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Signal Sources
export const addSignalSource = (url) =>
  client.post('/signal-sources', { url }).then((r) => r.data)

export const getSignalSources = () =>
  client.get('/signal-sources').then((r) => r.data)

export const deleteSignalSource = (id) =>
  client.delete(`/signal-sources/${id}`)

// Leads
export const getLeads = () =>
  client.get('/leads').then((r) => r.data)

export const getLeadTimeline = (id) =>
  client.get(`/leads/${id}`).then((r) => r.data).catch((e) => {
    if (e.response && e.response.status === 404) return null;
    throw e;
  })

export const deleteLead = (id) =>
  client.delete(`/leads/${id}`)

// Strategy
export const getStrategy = () =>
  client.get('/strategy').then((r) => r.data)

// Demo: qualify a person
export const qualifyPerson = (personId) =>
  client.post(`/demo/qualify/${personId}`).then((r) => r.data)

// Graph data (mock endpoint — falls back gracefully)
export const getGraphData = () =>
  client.get('/graph').catch(() => ({ data: { nodes: [], edges: [] } })).then((r) => r.data)
