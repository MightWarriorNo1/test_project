import { useState, useEffect, useCallback } from 'react'
import { fetchHealth, requestInference, getInferenceResult } from './api'
import type { InferenceResponse, MeterScore } from './types'
import './App.css'

function ScoreBadge({ score }: { score: number }) {
  const level = score >= 0.7 ? 'high' : score >= 0.4 ? 'medium' : 'low'
  return <span className={`badge ${level}`}>{(score * 100).toFixed(0)}%</span>
}

function FlaggedTable({ flagged }: { flagged: MeterScore[] }) {
  if (flagged.length === 0) {
    return <p className="empty">No flagged meters for this window.</p>
  }
  return (
    <table className="results-table">
      <thead>
        <tr>
          <th>Meter ID</th>
          <th>Anomaly score</th>
          <th>Reason code</th>
          <th>Primary factor</th>
        </tr>
      </thead>
      <tbody>
        {flagged.map((row) => (
          <tr key={row.meter_id}>
            <td>{row.meter_id}</td>
            <td><ScoreBadge score={row.anomaly_score} /></td>
            <td>{row.reason_code ?? '—'}</td>
            <td>{row.primary_factor ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function App() {
  const [healthOk, setHealthOk] = useState<boolean | null>(null)
  const [feederId, setFeederId] = useState('feeder-1')
  const [windowId, setWindowId] = useState('w1')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<InferenceResponse | null>(null)

  const checkHealth = useCallback(async () => {
    try {
      await fetchHealth()
      setHealthOk(true)
    } catch {
      setHealthOk(false)
    }
  }, [])

  useEffect(() => {
    checkHealth()
  }, [checkHealth])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
    setLoading(true)
    try {
      const data = await requestInference({ feeder_id: feederId, window_id: windowId })
      setResult(data)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Request failed'
      setError(msg)
      if (msg.includes('poll')) {
        let pollCount = 0
        const maxPoll = 10
        const interval = setInterval(async () => {
          pollCount++
          try {
            const res = await getInferenceResult(feederId, windowId)
            if (res) {
              setResult(res)
              setError(null)
              clearInterval(interval)
            } else if (pollCount >= maxPoll) {
              setError('Result not ready yet. Try again later.')
              clearInterval(interval)
            }
          } catch {
            if (pollCount >= maxPoll) clearInterval(interval)
          }
        }, 2000)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header>
        <h1>NTL Detection Engine</h1>
        <p className="subtitle">Non-Technical Loss detection — inference &amp; reason codes</p>
        <div className="health">
          <span className={`health-dot ${healthOk === true ? 'ok' : healthOk === false ? 'err' : ''}`} />
          {healthOk === true ? 'API connected' : healthOk === false ? 'API unreachable' : 'Checking…'}
        </div>
      </header>

      <section className="card">
        <h2>Request inference</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Feeder ID
              <input
                value={feederId}
                onChange={(e) => setFeederId(e.target.value)}
                placeholder="feeder-1"
              />
            </label>
            <label>
              Window ID
              <input
                value={windowId}
                onChange={(e) => setWindowId(e.target.value)}
                placeholder="w1"
              />
            </label>
          </div>
          <button type="submit" disabled={loading}>
            {loading ? 'Running…' : 'Run inference'}
          </button>
        </form>
        {error && <div className="message error">{error}</div>}
      </section>

      {result && (
        <section className="card">
          <h2>Results — {result.feeder_id} / {result.window_id}</h2>
          <p className="subtitle" style={{ marginBottom: '1rem' }}>Status: {result.status}</p>
          <FlaggedTable flagged={result.flagged} />
        </section>
      )}
    </div>
  )
}
