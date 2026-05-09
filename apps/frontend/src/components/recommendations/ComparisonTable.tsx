import type { ComparisonRow } from '@/types'
import clsx from 'clsx'

interface ComparisonTableProps {
  rows: ComparisonRow[]
  topPolicyName: string
}

export default function ComparisonTable({ rows, topPolicyName }: ComparisonTableProps) {
  if (rows.length === 0) return null

  const policyNames = Array.from(
    new Set(rows.flatMap((r) => Object.keys(r.values)))
  )

  return (
    <div className="overflow-x-auto rounded-xl ring-1 ring-gray-200">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
            <th className="px-4 py-3">Feature</th>
            {policyNames.map((name) => (
              <th
                key={name}
                className={clsx(
                  'px-4 py-3',
                  name === topPolicyName && 'text-brand-700',
                )}
              >
                {name}
                {name === topPolicyName && (
                  <span className="ml-1.5 rounded-full bg-brand-100 px-1.5 py-0.5 text-[10px] text-brand-700">
                    Top Pick
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((row, i) => (
            <tr key={i} className="bg-white hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 font-medium text-gray-700">{row.feature}</td>
              {policyNames.map((name) => (
                <td
                  key={name}
                  className={clsx(
                    'px-4 py-3 text-gray-600',
                    name === topPolicyName && 'font-medium text-gray-800',
                  )}
                >
                  {row.values[name] ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
