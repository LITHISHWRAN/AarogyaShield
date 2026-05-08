import { useEffect, useState } from 'react'
import { policiesApi } from '@/services/api'
import type { Policy } from '@/types'

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    policiesApi
      .list()
      .then((res) => setPolicies(res.data))
      .catch(() => setError('Failed to load policies.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-6 text-2xl font-bold text-brand-700">Available Policies</h1>

      {loading && <p className="text-gray-400">Loading…</p>}
      {error && <p className="text-red-500">{error}</p>}
      {!loading && !error && policies.length === 0 && (
        <p className="text-gray-500">No policies indexed yet. Upload via the Admin panel.</p>
      )}

      <ul className="space-y-4">
        {policies.map((p) => (
          <li key={p.id} className="rounded-xl bg-white p-5 shadow">
            <h2 className="font-semibold text-gray-900">{p.name}</h2>
            <p className="text-sm text-gray-500">{p.provider}</p>
            {p.description && <p className="mt-2 text-sm text-gray-700">{p.description}</p>}
          </li>
        ))}
      </ul>
    </div>
  )
}
