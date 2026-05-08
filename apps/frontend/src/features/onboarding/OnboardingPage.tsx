import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { useAppStore } from '@/store'
import type { UserProfile } from '@/types'

export default function OnboardingPage() {
  const navigate = useNavigate()
  const setUserProfile = useAppStore((s) => s.setUserProfile)

  const [form, setForm] = useState({
    age: '',
    income_bracket: '',
    pre_existing_conditions: '',
    family_size: '1',
    preferred_coverage: '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const profile: UserProfile = {
      age: Number(form.age),
      income_bracket: form.income_bracket,
      pre_existing_conditions: form.pre_existing_conditions
        ? form.pre_existing_conditions.split(',').map((s) => s.trim())
        : [],
      family_size: Number(form.family_size),
      preferred_coverage: form.preferred_coverage || undefined,
    }
    setUserProfile(profile)
    navigate('/chat')
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-lg">
        <h1 className="mb-1 text-2xl font-bold text-brand-700">AarogyaShield</h1>
        <p className="mb-6 text-sm text-gray-500">
          Tell us about yourself to get personalized health insurance recommendations.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            id="age"
            label="Age"
            type="number"
            min="1"
            max="100"
            required
            value={form.age}
            onChange={(e) => setForm({ ...form, age: e.target.value })}
          />
          <Input
            id="income_bracket"
            label="Income Bracket"
            placeholder="e.g. 3–6 LPA"
            required
            value={form.income_bracket}
            onChange={(e) => setForm({ ...form, income_bracket: e.target.value })}
          />
          <Input
            id="conditions"
            label="Pre-existing Conditions (comma-separated)"
            placeholder="e.g. diabetes, hypertension"
            value={form.pre_existing_conditions}
            onChange={(e) => setForm({ ...form, pre_existing_conditions: e.target.value })}
          />
          <Input
            id="family_size"
            label="Family Size"
            type="number"
            min="1"
            value={form.family_size}
            onChange={(e) => setForm({ ...form, family_size: e.target.value })}
          />
          <Input
            id="coverage"
            label="Preferred Coverage Type"
            placeholder="e.g. individual, family floater"
            value={form.preferred_coverage}
            onChange={(e) => setForm({ ...form, preferred_coverage: e.target.value })}
          />
          <Button type="submit" size="lg" className="mt-2">
            Get Recommendations
          </Button>
        </form>
      </div>
    </div>
  )
}
