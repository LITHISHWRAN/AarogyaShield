import { useState } from 'react'
import type { CitedChunk } from '@/types'

interface CitationCardProps {
  chunks: CitedChunk[]
}

export default function CitationCard({ chunks }: CitationCardProps) {
  const [open, setOpen] = useState(false)

  if (chunks.length === 0) return null

  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        {chunks.length} source{chunks.length > 1 ? 's' : ''} cited
        <span className="ml-0.5">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {chunks.map((chunk) => (
            <div
              key={chunk.index}
              className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs text-gray-600"
            >
              <p className="mb-1 font-medium text-gray-700">
                [{chunk.index}] {chunk.policy_name}
                <span className="ml-1 font-normal text-gray-400">· {chunk.insurer}</span>
              </p>
              <p className="leading-relaxed">{chunk.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
