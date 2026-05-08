export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface UserProfile {
  age: number
  income_bracket: string
  pre_existing_conditions: string[]
  family_size: number
  preferred_coverage?: string
}

export interface Policy {
  id: string
  name: string
  provider: string
  description?: string
}

export interface RecommendedPolicy {
  policy_id: string
  policy_name: string
  score: number
  rationale: string
  source_chunks: string[]
}

export interface RecommendationResponse {
  recommendations: RecommendedPolicy[]
  explanation: string
}
