import type { RecommendedPolicy } from '@/types'
import Card from '@/components/ui/Card'
import MatchScore from './MatchScore'
import JargonPill from './JargonPill'

interface PolicyCardProps {
  policy: RecommendedPolicy
  rank: 'top' | 'alternative'
}

export default function PolicyCard({ policy, rank }: PolicyCardProps) {
  const isTop = rank === 'top'
  const hasjargon = Object.keys(policy.jargon_definitions).length > 0

  return (
    <Card className={isTop ? 'ring-2 ring-brand-300' : ''}>
      {isTop && (
        <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-brand-600">
          Top Recommendation
        </p>
      )}

      <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-lg font-bold text-gray-900">{policy.policy_name}</h3>
          <p className="text-sm text-gray-500">{policy.insurer}</p>
        </div>
        <div className="min-w-[160px]">
          <MatchScore score={policy.match_score} />
        </div>
      </div>

      <p className="mb-4 text-sm italic text-gray-600">{policy.best_for}</p>

      <div className="mb-4 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-green-700">
            What's covered
          </p>
          <ul className="space-y-1.5">
            {policy.coverage_highlights.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="mt-0.5 shrink-0 text-green-500">✓</span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-700">
            Limitations to know
          </p>
          {policy.exclusions_noted.length > 0 ? (
            <ul className="space-y-1.5">
              {policy.exclusions_noted.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                  <span className="mt-0.5 shrink-0 text-amber-400">!</span>
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">No limitations noted in documents.</p>
          )}
        </div>
      </div>

      {hasjargon && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
            Terms defined from policy
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(policy.jargon_definitions).map(([term, def]) => (
              <JargonPill key={term} term={term} definition={def} />
            ))}
          </div>
        </div>
      )}
    </Card>
  )
}
