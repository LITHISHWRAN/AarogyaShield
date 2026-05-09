import { useState } from 'react'

interface JargonPillProps {
  term: string
  definition: string
}

export default function JargonPill({ term, definition }: JargonPillProps) {
  const [open, setOpen] = useState(false)

  return (
    <span className="relative inline-block">
      <button
        onClick={() => setOpen((v) => !v)}
        className="rounded-full border border-brand-200 bg-brand-50 px-2.5 py-0.5 text-xs font-medium text-brand-700 hover:bg-brand-100 transition-colors"
      >
        {term} {open ? '▲' : '▼'}
      </button>
      {open && (
        <span className="absolute left-0 top-7 z-10 w-64 rounded-xl border border-gray-200 bg-white p-3 text-xs text-gray-600 shadow-lg">
          <span className="mb-1 block font-semibold text-gray-800">{term}</span>
          {definition}
        </span>
      )}
    </span>
  )
}
