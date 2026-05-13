// ── User Profile ──────────────────────────────────────────────────────────────

export interface UserProfile {
  name: string
  age: number
  lifestyle: string
  pre_existing_conditions: string[]
  financial_band: string
  city_tier: string
  family_size: number
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface CitedChunk {
  index: number
  policy_name: string
  insurer: string
  text: string
}

/** Rich chat turn stored in local state — includes metadata returned by the backend */
export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
  intent?: string
  cited_chunks?: CitedChunk[]
  was_guardrailed?: boolean
  grounding_warnings?: string[]
}

export interface ChatResponse {
  session_id: string
  reply: string
  history: ChatMessage[]
  profile_loaded: boolean
  turn_count: number
  intent: string
  cited_chunks: CitedChunk[]
  was_guardrailed: boolean
  grounding_warnings: string[]
}

// ── Recommendations ───────────────────────────────────────────────────────────

export interface RecommendedPolicy {
  policy_id: string
  policy_name: string
  insurer: string
  match_score: number
  coverage_highlights: string[]
  exclusions_noted: string[]
  best_for: string
  citations: number[]
  jargon_definitions: Record<string, string>
}

export interface ComparisonRow {
  feature: string
  values: Record<string, string>
}

export interface SourceChunk {
  index: number
  policy_name: string
  insurer: string
  chunk_index: number
  text: string
}

export interface DecisionSummary {
  recommended: string
  top_reasons: string[]
  main_drawback: string
}

export interface RecommendationResponse {
  session_id: string
  top_recommendation: RecommendedPolicy | null
  alternatives: RecommendedPolicy[]
  comparison_table: ComparisonRow[]
  personalized_reasoning: string
  empathy_note: string
  decision_summary: DecisionSummary | null
  source_chunks: SourceChunk[]
  grounding_warnings: string[]
}

// ── Policies (public listing) ─────────────────────────────────────────────────

export interface Policy {
  id: string
  name: string
  provider: string
  description?: string
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export interface AdminPolicy {
  policy_id: string
  policy_name: string
  insurer: string
  file_type: string
  filename: string
  chunk_count: number
  source_document_id: string
  upload_date: string
}

export interface AdminUploadResponse {
  policy_id: string
  policy_name: string
  insurer: string
  file_type: string
  filename: string
  chunks_indexed: number
  upload_date: string
  message: string
}

export interface AdminDeleteResponse {
  policy_id: string
  vectors_removed: number
  message: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}
