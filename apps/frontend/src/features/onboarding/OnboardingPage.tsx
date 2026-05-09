import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Alert from '@/components/ui/Alert'
import Spinner from '@/components/ui/Spinner'
import { recommendApi } from '@/services/api'
import { useAppStore } from '@/store'
import type { UserProfile } from '@/types'

const COMMON_CONDITIONS = [
  'Diabetes', 'Hypertension', 'Heart Disease', 'Asthma',
  'Thyroid Disorder', 'Kidney Disease', 'Cancer (history)', 'Arthritis',
]

const LIFESTYLE_OPTIONS = [
  { value: 'sedentary', label: 'Mostly desk work / low activity' },
  { value: 'active', label: 'Regularly active / exercises' },
  { value: 'smoker', label: 'Smoker' },
  { value: 'athlete', label: 'Athlete or high-risk sports' },
]

const FINANCIAL_BANDS = [
  'Up to 3 LPA', '3–6 LPA', '6–10 LPA', '10–15 LPA', '15+ LPA',
]

const CITY_TIERS = [
  { value: 'Tier 1', label: 'Tier 1 — Mumbai, Delhi, Bengaluru, Chennai…' },
  { value: 'Tier 2', label: 'Tier 2 — Pune, Jaipur, Lucknow, Kochi…' },
  { value: 'Tier 3', label: 'Tier 3 — Smaller cities and towns' },
]

export default function OnboardingPage() {
  const navigate = useNavigate()
  const { sessionId, setUserProfile, setRecommendations } = useAppStore()

  const [name, setName] = useState('')
  const [age, setAge] = useState('')
  const [lifestyle, setLifestyle] = useState('sedentary')
  const [selectedConditions, setSelectedConditions] = useState<string[]>([])
  const [otherCondition, setOtherCondition] = useState('')
  const [financialBand, setFinancialBand] = useState('')
  const [cityTier, setCityTier] = useState('Tier 1')
  const [familySize, setFamilySize] = useState('1')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const toggleCondition = (c: string) => {
    if (c === 'None') {
      setSelectedConditions(['None'])
      return
    }
    setSelectedConditions((prev) => {
      const without = prev.filter((x) => x !== 'None')
      return without.includes(c) ? without.filter((x) => x !== c) : [...without, c]
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!name.trim() || !age || !financialBand) {
      setError('Please fill in all required fields.')
      return
    }

    const conditions = selectedConditions.filter((c) => c !== 'None')
    if (otherCondition.trim()) {
      conditions.push(...otherCondition.split(',').map((s) => s.trim()).filter(Boolean))
    }

    const profile: UserProfile = {
      name: name.trim(),
      age: Number(age),
      lifestyle,
      pre_existing_conditions: conditions,
      financial_band: financialBand,
      city_tier: cityTier,
      family_size: Number(familySize),
    }

    setUserProfile(profile)
    setLoading(true)

    try {
      const res = await recommendApi.get(sessionId, profile)
      setRecommendations(res.data)
      navigate('/recommendations')
    } catch {
      setError('We could not find recommendations right now. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 to-white px-4 py-12">
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="mb-10 text-center">
          <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-600 text-white text-xl font-bold shadow">
            A
          </div>
          <h1 className="text-3xl font-bold text-gray-900">AarogyaShield</h1>
          <p className="mt-2 text-gray-500">
            Let's find the right health plan for you — honestly, transparently.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Section 1: Basic Info */}
          <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-gray-100">
            <h2 className="mb-1 font-semibold text-gray-800">About you</h2>
            <p className="mb-5 text-sm text-gray-500">
              We use this to personalise your results — nothing is shared.
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                id="name"
                label="Your name *"
                placeholder="e.g. Arjun Sharma"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <Input
                id="age"
                label="Age *"
                type="number"
                min="1"
                max="100"
                required
                value={age}
                onChange={(e) => setAge(e.target.value)}
              />
              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium text-gray-700">Family size</label>
                <Input
                  id="family_size"
                  type="number"
                  min="1"
                  max="20"
                  value={familySize}
                  onChange={(e) => setFamilySize(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium text-gray-700">City tier</label>
                <select
                  value={cityTier}
                  onChange={(e) => setCityTier(e.target.value)}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  {CITY_TIERS.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </section>

          {/* Section 2: Health */}
          <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-gray-100">
            <h2 className="mb-1 font-semibold text-gray-800">Your health profile</h2>
            <p className="mb-5 text-sm text-gray-500">
              No judgment here — disclosing pre-existing conditions helps us find plans that
              actually cover you, rather than ones that will reject your claims later.
            </p>

            <div className="mb-5">
              <p className="mb-3 text-sm font-medium text-gray-700">
                Pre-existing conditions (select all that apply)
              </p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {COMMON_CONDITIONS.map((c) => (
                  <label
                    key={c}
                    className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2.5 text-sm transition-colors ${
                      selectedConditions.includes(c)
                        ? 'border-brand-400 bg-brand-50 text-brand-800'
                        : 'border-gray-200 bg-white text-gray-600 hover:border-brand-200'
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="sr-only"
                      checked={selectedConditions.includes(c)}
                      onChange={() => toggleCondition(c)}
                    />
                    <span className={`text-base ${selectedConditions.includes(c) ? 'text-brand-500' : 'text-gray-300'}`}>
                      {selectedConditions.includes(c) ? '✓' : '○'}
                    </span>
                    {c}
                  </label>
                ))}
              </div>
              <Input
                id="other_condition"
                className="mt-3"
                placeholder="Other conditions, comma-separated (optional)"
                value={otherCondition}
                onChange={(e) => setOtherCondition(e.target.value)}
              />
            </div>

            <div>
              <p className="mb-3 text-sm font-medium text-gray-700">Lifestyle</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {LIFESTYLE_OPTIONS.map((opt) => (
                  <label
                    key={opt.value}
                    className={`flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 text-sm transition-colors ${
                      lifestyle === opt.value
                        ? 'border-brand-400 bg-brand-50 text-brand-800'
                        : 'border-gray-200 bg-white text-gray-600 hover:border-brand-200'
                    }`}
                  >
                    <input
                      type="radio"
                      className="sr-only"
                      name="lifestyle"
                      value={opt.value}
                      checked={lifestyle === opt.value}
                      onChange={() => setLifestyle(opt.value)}
                    />
                    <span className="text-base">
                      {lifestyle === opt.value ? '●' : '○'}
                    </span>
                    {opt.label}
                  </label>
                ))}
              </div>
            </div>
          </section>

          {/* Section 3: Financial */}
          <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-gray-100">
            <h2 className="mb-1 font-semibold text-gray-800">Your budget</h2>
            <p className="mb-5 text-sm text-gray-500">
              Annual income determines the premium range that's comfortable for you.
            </p>
            <div>
              <p className="mb-3 text-sm font-medium text-gray-700">Annual income band *</p>
              <div className="flex flex-wrap gap-2">
                {FINANCIAL_BANDS.map((band) => (
                  <button
                    key={band}
                    type="button"
                    onClick={() => setFinancialBand(band)}
                    className={`rounded-xl border px-4 py-2 text-sm font-medium transition-colors ${
                      financialBand === band
                        ? 'border-brand-500 bg-brand-600 text-white'
                        : 'border-gray-200 bg-white text-gray-600 hover:border-brand-300'
                    }`}
                  >
                    {band}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {error && <Alert variant="error">{error}</Alert>}

          <Button
            type="submit"
            size="lg"
            className="w-full"
            disabled={loading}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <Spinner size="sm" className="text-white" />
                Finding the right plans for you…
              </span>
            ) : (
              'Show my recommendations →'
            )}
          </Button>

          <p className="text-center text-xs text-gray-400">
            Recommendations are based on policy documents — no sponsored results.
          </p>
        </form>
      </div>
    </div>
  )
}
