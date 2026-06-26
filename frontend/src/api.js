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
    if (e.response && e.response.status === 404) return null
    throw e
  })

export const deleteLead = (id) =>
  client.delete(`/leads/${id}`)

export const approveLeadAction = (leadId, actionId) =>
  client.patch(`/leads/${leadId}/actions/${actionId}/approve`).then((r) => r.data)

// Strategy
export const getStrategy = () =>
  client.get('/strategy').then((r) => r.data)

// Demo: qualify a person
export const qualifyPerson = (personId) =>
  client.post(`/demo/qualify/${personId}`).then((r) => r.data)

// Graph data - wired to real /graph endpoint
export const getGraphData = () =>
  client.get('/graph').then((r) => r.data)
