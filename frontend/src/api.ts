import type { HealthResponse, InferenceRequest, InferenceResponse } from './types'

const getBaseUrl = (): string => {
  const url = import.meta.env.VITE_API_URL
  if (url) return url.replace(/\/$/, '')
  return '/api'
}

export async function fetchHealth(): Promise<HealthResponse> {
  const base = getBaseUrl()
  const res = await fetch(`${base}/health`)
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return res.json()
}

export async function requestInference(req: InferenceRequest): Promise<InferenceResponse> {
  const base = getBaseUrl()
  const res = await fetch(`${base}/inference`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  const data = await res.json().catch(() => ({}))
  if (res.status === 202) {
    throw new Error(data.detail || 'Inference queued; poll for result.')
  }
  if (!res.ok) throw new Error(data.detail || `Request failed: ${res.status}`)
  return data as InferenceResponse
}

export async function getInferenceResult(
  feederId: string,
  windowId: string
): Promise<InferenceResponse | null> {
  const base = getBaseUrl()
  const res = await fetch(`${base}/inference/${encodeURIComponent(feederId)}/${encodeURIComponent(windowId)}`)
  if (res.status === 404 || res.status === 204) return null
  if (!res.ok) throw new Error(`Poll failed: ${res.status}`)
  return res.json() as Promise<InferenceResponse>
}
