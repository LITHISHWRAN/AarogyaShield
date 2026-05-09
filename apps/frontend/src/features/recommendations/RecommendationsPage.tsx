import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAppStore } from '@/store'
import PolicyCard from '@/components/recommendations/PolicyCard'
import ComparisonTable from '@/components/recommendations/ComparisonTable'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'

export default function RecommendationsPage() {
  const navigate = useNavigate()
  const { recommendations, userProfile } = useAppStore()

  useEffect(() => {
    if (!recommendations) navigate('/')
  }, [recommendations, navigate])

  if (!recommendations) return null

  const { top_recommendation, alternatives, comparison_table, personalized_reasoning, empathy_note, source_chunks, grounding_warnings } = recommendations

  const hasNoData = !top_recommendation

  return (
    <div className="min-h-screen bg-gray-50 pb-16">
      {/* Header */}
      <div className="bg-white border-b px-6 py-5">
        <div className="mx-auto max-w-4xl flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              {userProfile ? `Your plans, ${userProfile.name}` : 'Your recommendations'}
            </h1>
            <p className="text-sm text-gray-500">Based on your profile and uploaded policy documents</p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => navigate('/')}>
              Update profile
            </Button>
            <Button size="sm" onClick={() => navigate('/chat')}>
              Chat with advisor →
            </Button>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-4xl px-4 py-8 space-y-8">

        {/* Grounding warnings */}
        {grounding_warnings.length > 0 && (
          <Alert variant="warning" title="Transparency notice">
            <ul className="mt-1 list-disc list-inside space-y-0.5 text-xs">
              {grounding_warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </Alert>
        )}

        {/* No data */}
        {hasNoData && (
          <Alert variant="info" title="No policies indexed yet">
            No policy documents have been uploaded. Please ask an administrator to add policy
            files, then try again.
          </Alert>
        )}

        {/* Empathy note */}
        {empathy_note && (
          <div className="rounded-2xl bg-brand-50 px-6 py-4 text-sm text-brand-800 border border-brand-100">
            {empathy_note}
          </div>
        )}

        {/* Top recommendation */}
        {top_recommendation && (
          <div>
            <PolicyCard policy={top_recommendation} rank="top" />
          </div>
        )}

        {/* Personalized reasoning */}
        {personalized_reasoning && (
          <Card>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">
              Why this plan fits you
            </h2>
            <p className="text-sm leading-relaxed text-gray-700">{personalized_reasoning}</p>
          </Card>
        )}

        {/* Alternatives */}
        {alternatives.length > 0 && (
          <div>
            <h2 className="mb-4 font-semibold text-gray-700">Other plans to consider</h2>
            <div className="space-y-4">
              {alternatives.map((alt) => (
                <PolicyCard key={alt.policy_id} policy={alt} rank="alternative" />
              ))}
            </div>
          </div>
        )}

        {/* Comparison table */}
        {comparison_table.length > 0 && top_recommendation && (
          <div>
            <h2 className="mb-4 font-semibold text-gray-700">Side-by-side comparison</h2>
            <ComparisonTable
              rows={comparison_table}
              topPolicyName={top_recommendation.policy_name}
            />
          </div>
        )}

        {/* Source documents */}
        {source_chunks.length > 0 && (
          <details className="group">
            <summary className="flex cursor-pointer items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-700">
              <span>View source documents ({source_chunks.length} excerpts)</span>
              <span className="text-gray-400 group-open:rotate-180 transition-transform">▼</span>
            </summary>
            <div className="mt-4 space-y-3">
              {source_chunks.map((chunk) => (
                <div
                  key={chunk.index}
                  className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600"
                >
                  <p className="mb-2 font-medium text-gray-800">
                    [{chunk.index}] {chunk.policy_name}
                    <span className="ml-2 font-normal text-gray-400">{chunk.insurer}</span>
                  </p>
                  <p className="leading-relaxed">{chunk.text}</p>
                </div>
              ))}
            </div>
          </details>
        )}

        {/* Grounding footnote */}
        <p className="text-center text-xs text-gray-400">
          All facts above are sourced directly from uploaded policy documents.
          No information has been inferred or fabricated.
        </p>

        {/* CTA */}
        <div className="rounded-2xl bg-brand-600 p-6 text-center text-white">
          <h3 className="text-lg font-semibold">Have questions about these plans?</h3>
          <p className="mt-1 text-sm text-brand-100">
            AarogyaAid can explain any term, coverage detail, or exclusion — with citations.
          </p>
          <Button
            variant="secondary"
            className="mt-4"
            onClick={() => navigate('/chat')}
          >
            Chat with AarogyaAid →
          </Button>
        </div>
      </div>
    </div>
  )
}
