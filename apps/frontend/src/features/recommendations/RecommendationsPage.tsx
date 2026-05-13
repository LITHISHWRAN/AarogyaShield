import { useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAppStore } from '@/store'

const stripCitations = (text: string) => text.replace(/\s*\[[\d,\s]+\]/g, '')
import PolicyCard from '@/components/recommendations/PolicyCard'
import ComparisonTable from '@/components/recommendations/ComparisonTable'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import type { DecisionSummary } from '@/types'

function DecisionSummaryCard({ summary }: { summary: DecisionSummary }) {
  return (
    <Card className="border-brand-200 bg-brand-50">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-brand-600">
            Recommended
          </p>
          <p className="text-lg font-bold text-gray-900">{summary.recommended}</p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-green-700">Why</p>
          <ul className="space-y-1">
            {summary.top_reasons.map((r, i) => (
              <li key={i} className="flex items-start gap-1.5 text-sm text-gray-700">
                <span className="mt-0.5 shrink-0 text-green-500">✓</span>
                {stripCitations(r)}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-amber-700">Main drawback</p>
          <p className="flex items-start gap-1.5 text-sm text-gray-600">
            <span className="mt-0.5 shrink-0 text-amber-400">!</span>
            {stripCitations(summary.main_drawback)}
          </p>
        </div>
      </div>
    </Card>
  )
}

export default function RecommendationsPage() {
  const navigate = useNavigate()
  const { recommendations, userProfile } = useAppStore()
  const [reasoningOpen, setReasoningOpen] = useState(false)

  useEffect(() => {
    if (!recommendations) navigate('/')
  }, [recommendations, navigate])

  if (!recommendations) return null

  const { top_recommendation, alternatives, comparison_table, personalized_reasoning, empathy_note, decision_summary, grounding_warnings } = recommendations

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
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/')}
              className="text-xs text-gray-500 hover:text-gray-800 border border-gray-200 hover:border-gray-300 rounded-lg px-3 py-1.5 transition-colors whitespace-nowrap"
            >
              Update profile
            </button>
            <button
              onClick={() => navigate('/chat')}
              className="text-xs text-white bg-brand-600 hover:bg-brand-700 rounded-lg px-3 py-1.5 transition-colors whitespace-nowrap font-medium"
            >
              Chat with ShieldCare →
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-4xl px-4 py-8 space-y-8">

        {/* Grounding warnings — only show citation fabrication issues, not internal profile checks */}
        {grounding_warnings.some(w => w.includes("does not exist in the retrieved context")) && (
          <Alert variant="warning" title="Transparency notice">
            <ul className="mt-1 list-disc list-inside space-y-0.5 text-xs">
              {grounding_warnings
                .filter(w => w.includes("does not exist in the retrieved context"))
                .map((w, i) => <li key={i}>{w}</li>)}
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
            {stripCitations(empathy_note)}
          </div>
        )}

        {/* Decision summary — concise verdict before full details */}
        {decision_summary && <DecisionSummaryCard summary={decision_summary} />}

        {/* Top recommendation */}
        {top_recommendation && (
          <div>
            <PolicyCard policy={top_recommendation} rank="top" />
          </div>
        )}

        {/* Personalized reasoning — collapsed by default */}
        {personalized_reasoning && (
          <Card>
            <button
              onClick={() => setReasoningOpen(v => !v)}
              className="flex w-full items-center justify-between text-left"
            >
              <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-400">
                Why this plan fits you
              </h2>
              <span className={`text-gray-400 transition-transform text-xs ${reasoningOpen ? 'rotate-180' : ''}`}>▼</span>
            </button>
            {reasoningOpen && (
              <p className="mt-3 text-sm leading-relaxed text-gray-700">{stripCitations(personalized_reasoning)}</p>
            )}
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


        {/* Grounding footnote */}
        <p className="text-center text-xs text-gray-400">
          All facts above are sourced directly from uploaded policy documents.
          No information has been inferred or fabricated.
        </p>

        {/* CTA */}
        <div className="rounded-2xl bg-brand-600 p-6 text-center text-white">
          <h3 className="text-lg font-semibold">Have questions about these plans?</h3>
          <p className="mt-1 text-sm text-brand-100">
            ShieldCare can explain any term, coverage detail, or exclusion — with citations.
          </p>
          <Button
            variant="secondary"
            className="mt-4"
            onClick={() => navigate('/chat')}
          >
            Chat with ShieldCare →
          </Button>
        </div>
      </div>
    </div>
  )
}
