import type { components } from './openapi-types'

export type LoginData = components['schemas']['LoginRequest']

// Form shape (includes confirmPassword)
export interface RegisterData {
  email: string
  password: string
  confirmPassword: string
}

// API payload shape for registration
export type RegisterPayload = components['schemas']['RegisterRequest']

export type User = components['schemas']['UserResponse'] & { created_at?: string }

export interface ApiError {
  detail?: string
  message?: string
  code?: string
}

export interface PlanInfo {
  slug: string
  name: string
  price_cents: number
  query_qps_limit: number
  ingest_qps_limit: number
  project_limit: number | null
  vector_limit: number | null
}

export interface UsageInfo {
  total_queries: number
  total_ingest_requests: number
  total_vectors: number
  project_count: number
  project_limit: number | null
  vector_limit: number | null
}

export interface ProjectSummary {
  id: number
  name: string
  description?: string | null
  slug?: string | null
  embedding_provider: string
  embedding_model: string
  embedding_model_repo?: string | null
  embedding_model_file?: string | null
  embedding_dim: number
  hybrid_weight_vector: number
  hybrid_weight_text: number
  top_k_default: number
  vector_search_k: number
  vector_count: number
  vector_store_path: string
}

export interface ProjectsOnload {
  projects: ProjectSummary[]
  usage: UsageInfo
  plan: PlanInfo | null
  needs_subscription: boolean
}

export interface ProjectCreatePayload {
  name: string
  description?: string
  embedding_provider?: string
  embedding_model?: string
  embedding_model_repo?: string
  embedding_model_file?: string
  embedding_dim?: number
  hybrid_weight_vector?: number
  hybrid_weight_text?: number
  top_k_default?: number
  vector_search_k?: number
}

export interface ProjectCreateResponse {
  project: ProjectSummary
  ingest_api_key: string
}

export interface ProjectRotateKeyResponse {
  project_id: number
  ingest_api_key: string
}
