import clsx from 'clsx'

interface MatchScoreProps {
  score: number   // 0–1
  showLabel?: boolean
}

export default function MatchScore({ score, showLabel = true }: MatchScoreProps) {
  const pct = Math.round(score * 100)
  const barColor =
    pct >= 75 ? 'bg-brand-600' : pct >= 50 ? 'bg-brand-400' : 'bg-amber-400'
  const textColor =
    pct >= 75 ? 'text-brand-700' : pct >= 50 ? 'text-brand-600' : 'text-amber-600'

  return (
    <div className="flex items-center gap-3">
      <div className="h-2 flex-1 rounded-full bg-gray-100">
        <div
          className={clsx('h-2 rounded-full transition-all', barColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <span className={clsx('text-sm font-semibold tabular-nums', textColor)}>
          {pct}% match
        </span>
      )}
    </div>
  )
}
