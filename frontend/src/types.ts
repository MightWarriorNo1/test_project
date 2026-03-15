export interface MeterScore {
  meter_id: string
  anomaly_score: number
  reason_code?: string
  primary_factor?: string
}

export interface InferenceResponse {
  feeder_id: string
  window_id: string
  flagged: MeterScore[]
  status: string
}

export interface InferenceRequest {
  feeder_id: string
  window_id: string
  topology_version?: string
}

export interface HealthResponse {
  status: string
}
