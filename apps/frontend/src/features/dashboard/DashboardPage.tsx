import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '@/store'
import { chatApi } from '@/services/api'
import type { DecisionSummary } from '@/types'

import PolicyCard from '@/components/recommendations/PolicyCard'
import ComparisonTable from '@/components/recommendations/ComparisonTable'
import Spinner from '@/components/ui/Spinner'

const strip = (t: string) => t.replace(/\s*\[[\d,\s]+\]/g, '')

const QUICK_PROMPTS = [
  'What does my recommended plan cover?',
  'Explain the waiting period',
  "What's not covered?",
  'How do I file a claim?',
  'What is a co-payment?',
  'Does it cover my condition?',
]

function SummaryCard({ summary }: { summary: DecisionSummary }) {
  return (
    <div className="rounded-2xl bg-white border border-gray-100 shadow-sm p-5">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-widest text-brand-600">
            Top Pick
          </span>
          <h3 className="mt-0.5 text-base font-bold text-gray-900 leading-tight">
            {strip(summary.recommended)}
          </h3>
        </div>
        <span className="shrink-0 rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700 border border-brand-100">
          Recommended
        </span>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          {summary.top_reasons.map((r, i) => (
            <div key={i} className="flex items-start gap-2 text-sm text-gray-600">
              <svg className="mt-0.5 h-4 w-4 shrink-0 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              {strip(r)}
            </div>
          ))}
        </div>
        <div className="rounded-xl bg-amber-50 border border-amber-100 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-700 mb-1">Watch out</p>
          <p className="text-xs text-amber-800 leading-relaxed">{strip(summary.main_drawback)}</p>
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { sessionId, userProfile, recommendations, chatTurns, addChatTurn } = useAppStore()

  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [reasoningOpen, setReasoningOpen] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!recommendations) navigate('/')
  }, [recommendations, navigate])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatTurns, loading])

  const send = async (text: string) => {
    const msg = text.trim()
    if (!msg || loading) return
    setInput('')
    addChatTurn({ role: 'user', content: msg })
    setLoading(true)
    try {
      const res = await chatApi.send(
        sessionId,
        msg,
        chatTurns.length === 0 && userProfile ? userProfile : undefined,
      )
      const d = res.data
      addChatTurn({
        role: 'assistant',
        content: d.reply,
        intent: d.intent,
        cited_chunks: d.cited_chunks,
        was_guardrailed: d.was_guardrailed,
        grounding_warnings: d.grounding_warnings,
      })
    } catch {
      addChatTurn({ role: 'assistant', content: 'Sorry, something went wrong. Please try again.' })
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  if (!recommendations) return null

  const {
    top_recommendation,
    alternatives,
    comparison_table,
    personalized_reasoning,
    empathy_note,
    decision_summary,
  } = recommendations

  const initial = userProfile?.name?.[0]?.toUpperCase() ?? 'U'

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-gray-50">

      {/* ── Top Header ── */}
      <header className="shrink-0 h-14 bg-white border-b border-gray-100 px-6 flex items-center justify-between shadow-sm z-10">
        <div className="flex items-center gap-3">
          <img src="/logo.png" alt="AarogyaShield" className="h-8 w-8 object-contain" />
          <span className="font-bold text-gray-900 text-sm tracking-tight">AarogyaShield</span>
        </div>
        <div className="flex items-center gap-4">
          {userProfile && (
            <div className="hidden sm:flex items-center gap-2 text-sm text-gray-500">
              <div className="h-6 w-6 rounded-full bg-brand-100 flex items-center justify-center text-xs font-bold text-brand-700">
                {initial}
              </div>
              <span>{userProfile.name}</span>
            </div>
          )}
          <button
            onClick={() => navigate('/')}
            className="text-xs text-gray-400 hover:text-gray-700 transition-colors border border-gray-200 rounded-lg px-3 py-1.5 hover:border-gray-300"
          >
            Update profile
          </button>
        </div>
      </header>

      {/* ── Body ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* ══ LEFT PANEL: Recommendations ══ */}
        <div className="flex-1 overflow-y-auto bg-gray-50">
          <div className="max-w-2xl mx-auto px-6 py-6 space-y-5">

            {/* Empathy note */}
            {empathy_note && (
              <div className="flex gap-3 rounded-2xl bg-white border border-gray-100 shadow-sm px-5 py-4">
                <div className="shrink-0 mt-0.5">
                  <div className="h-7 w-7 rounded-full bg-brand-600 flex items-center justify-center">
                    <svg className="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                    </svg>
                  </div>
                </div>
                <p className="text-sm text-gray-600 leading-relaxed">{strip(empathy_note)}</p>
              </div>
            )}

            {/* Decision summary */}
            {decision_summary && <SummaryCard summary={decision_summary} />}

            {/* Top recommendation */}
            {top_recommendation && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3 px-1">
                  Best match for you
                </p>
                <PolicyCard policy={top_recommendation} rank="top" />
              </div>
            )}

            {/* Why this fits — collapsible */}
            {personalized_reasoning && (
              <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
                <button
                  onClick={() => setReasoningOpen(v => !v)}
                  className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50 transition-colors"
                >
                  <span className="text-sm font-semibold text-gray-700">Why this plan fits you</span>
                  <svg
                    className={`h-4 w-4 text-gray-400 transition-transform duration-200 ${reasoningOpen ? 'rotate-180' : ''}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {reasoningOpen && (
                  <div className="px-5 pb-5 border-t border-gray-50">
                    <p className="mt-4 text-sm text-gray-600 leading-relaxed">
                      {strip(personalized_reasoning)}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Alternatives */}
            {alternatives.length > 0 && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3 px-1">
                  Other plans to consider
                </p>
                <div className="space-y-4">
                  {alternatives.map(alt => (
                    <PolicyCard key={alt.policy_id} policy={alt} rank="alternative" />
                  ))}
                </div>
              </div>
            )}

            {/* Comparison table */}
            {comparison_table.length > 0 && top_recommendation && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3 px-1">
                  Side-by-side comparison
                </p>
                <ComparisonTable rows={comparison_table} topPolicyName={top_recommendation.policy_name} />
              </div>
            )}

            <p className="text-center text-[11px] text-gray-300 pb-4">
              Sourced from uploaded policy documents · Nothing inferred or fabricated
            </p>
          </div>
        </div>

        {/* ══ RIGHT PANEL: Chat ══ */}
        <div className="w-[380px] shrink-0 flex flex-col bg-white border-l border-gray-100 shadow-[-8px_0_24px_rgba(0,0,0,0.04)]">

          {/* Chat panel header */}
          <div className="shrink-0 px-5 py-4 border-b border-gray-100 bg-white">
            <div className="flex items-center gap-3">
              <div className="relative">
                <img src="/logo.png" alt="ShieldCare" className="h-9 w-9 object-contain rounded-full" />
                <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-green-400 ring-2 ring-white" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">ShieldCare</p>
                <p className="text-xs text-green-500 font-medium">Online · Ask anything</p>
              </div>
            </div>
          </div>

          {/* Messages area */}
          <div className="flex-1 overflow-y-auto px-4 py-5 space-y-4 bg-gray-50">

            {/* Empty state */}
            {chatTurns.length === 0 && !loading && (
              <div className="space-y-4">
                <div className="flex items-start gap-2.5">
                  <img src="/logo.png" alt="A" className="shrink-0 h-7 w-7 rounded-full object-contain mt-0.5" />
                  <div className="bg-white rounded-2xl rounded-tl-sm shadow-sm border border-gray-100 px-4 py-3 max-w-[85%]">
                    <p className="text-sm text-gray-700 leading-relaxed">
                      {userProfile
                        ? `Hi ${userProfile.name}! I've reviewed your profile and found the best plans for you. What would you like to know?`
                        : "Hi! I've found some plans for you. Feel free to ask me anything about them."}
                    </p>
                  </div>
                </div>

                <p className="text-[11px] font-semibold uppercase tracking-widest text-gray-400 px-1 mt-2">
                  Quick questions
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {QUICK_PROMPTS.map(p => (
                    <button
                      key={p}
                      onClick={() => send(p)}
                      className="rounded-xl bg-white border border-gray-200 px-3 py-2.5 text-left text-xs text-gray-600 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 transition-all shadow-sm leading-relaxed"
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Turns */}
            {chatTurns.map((turn, i) => (
              <div
                key={i}
                className={`flex items-end gap-2 ${turn.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {turn.role === 'assistant' && (
                  <div className="shrink-0 h-7 w-7 rounded-full bg-brand-600 flex items-center justify-center text-[11px] font-bold text-white mb-0.5 shadow-sm">
                    A
                  </div>
                )}
                <div
                  className={`max-w-[80%] px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
                    turn.role === 'user'
                      ? 'bg-brand-600 text-white rounded-2xl rounded-br-sm'
                      : turn.was_guardrailed
                      ? 'bg-amber-50 text-amber-900 border border-amber-200 rounded-2xl rounded-bl-sm'
                      : 'bg-white text-gray-800 border border-gray-100 rounded-2xl rounded-bl-sm'
                  }`}
                >
                  {turn.role === 'assistant' ? strip(turn.content) : turn.content}
                  {turn.was_guardrailed && (
                    <p className="mt-1.5 text-[11px] text-amber-600 font-medium">
                      ⚠ Redirected for your safety
                    </p>
                  )}
                </div>
                {turn.role === 'user' && (
                  <div className="shrink-0 h-7 w-7 rounded-full bg-gray-200 flex items-center justify-center text-[11px] font-bold text-gray-600 mb-0.5">
                    {initial}
                  </div>
                )}
              </div>
            ))}

            {/* Typing indicator */}
            {loading && (
              <div className="flex items-end gap-2">
                <div className="shrink-0 h-7 w-7 rounded-full bg-brand-600 flex items-center justify-center text-[11px] font-bold text-white shadow-sm">
                  A
                </div>
                <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                  <div className="flex gap-1 items-center h-4">
                    <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
                    <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
                    <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="shrink-0 bg-white border-t border-gray-100 px-4 py-3">
            <div className="flex items-center gap-2 bg-gray-50 rounded-2xl border border-gray-200 pr-1.5 pl-4 focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-100 transition-all">
              <input
                ref={inputRef}
                type="text"
                className="flex-1 bg-transparent py-2.5 text-sm text-gray-800 placeholder-gray-400 focus:outline-none"
                placeholder="Ask about your plans…"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && send(input)}
                disabled={loading}
              />
              <button
                onClick={() => send(input)}
                disabled={loading || !input.trim()}
                className="shrink-0 h-8 w-8 rounded-xl bg-brand-600 flex items-center justify-center text-white hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm"
              >
                {loading
                  ? <Spinner size="sm" className="text-white" />
                  : (
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.269 20.876L5.999 12zm0 0h7.5" />
                    </svg>
                  )
                }
              </button>
            </div>
            <p className="mt-2 text-center text-[10px] text-gray-300">
              Grounded in policy documents · Not medical advice
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
