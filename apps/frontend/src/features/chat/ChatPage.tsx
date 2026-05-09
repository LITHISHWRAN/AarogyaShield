import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import Alert from '@/components/ui/Alert'
import CitationCard from '@/components/chat/CitationCard'
import IntentBadge from '@/components/chat/IntentBadge'
import TypingIndicator from '@/components/chat/TypingIndicator'
import { chatApi } from '@/services/api'
import { useAppStore } from '@/store'
import type { ChatTurn } from '@/types'

const QUICK_PROMPTS = [
  'What does my recommended plan cover?',
  'Explain the waiting period',
  "What's not covered in my plan?",
  'How do I make a cashless claim?',
  'What is a co-payment?',
  'Does it cover my pre-existing condition?',
]

export default function ChatPage() {
  const navigate = useNavigate()
  const { sessionId, userProfile, recommendations, chatTurns, addChatTurn } = useAppStore()
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatTurns, loading])

  const send = async (text: string) => {
    const msg = text.trim()
    if (!msg || loading) return
    setInput('')
    setError('')

    addChatTurn({ role: 'user', content: msg })
    setLoading(true)

    try {
      const res = await chatApi.send(
        sessionId,
        msg,
        chatTurns.length === 0 && userProfile ? userProfile : undefined,
      )
      const data = res.data
      addChatTurn({
        role: 'assistant',
        content: data.reply,
        intent: data.intent,
        cited_chunks: data.cited_chunks,
        was_guardrailed: data.was_guardrailed,
        grounding_warnings: data.grounding_warnings,
      })
    } catch {
      setError('Something went wrong. Please try again.')
      addChatTurn({ role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' })
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const conditions = userProfile?.pre_existing_conditions.join(', ') || 'none declared'

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col border-r bg-white lg:flex">
        <div className="border-b p-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-600 text-sm font-bold text-white">
              A
            </div>
            <span className="font-semibold text-brand-700">AarogyaAid</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {userProfile ? (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
                Your profile
              </p>
              <div className="rounded-xl bg-gray-50 p-3 text-xs text-gray-600 space-y-1">
                <p><span className="font-medium">Name:</span> {userProfile.name}</p>
                <p><span className="font-medium">Age:</span> {userProfile.age}</p>
                <p><span className="font-medium">Band:</span> {userProfile.financial_band}</p>
                <p><span className="font-medium">Tier:</span> {userProfile.city_tier}</p>
                <p><span className="font-medium">Conditions:</span> {conditions}</p>
              </div>
            </div>
          ) : (
            <div className="rounded-xl bg-amber-50 p-3 text-xs text-amber-700">
              No profile loaded. Answers may be less personalised.
            </div>
          )}

          {recommendations?.top_recommendation && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
                Top recommendation
              </p>
              <div className="rounded-xl bg-brand-50 p-3 text-xs text-brand-800 space-y-1">
                <p className="font-semibold">{recommendations.top_recommendation.policy_name}</p>
                <p>{recommendations.top_recommendation.insurer}</p>
                <p className="text-brand-600">
                  {Math.round(recommendations.top_recommendation.match_score * 100)}% match
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="border-t p-4 space-y-2">
          <Button
            variant="secondary"
            size="sm"
            className="w-full"
            onClick={() => navigate('/recommendations')}
          >
            View recommendations
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="w-full"
            onClick={() => navigate('/')}
          >
            Update profile
          </Button>
        </div>
      </aside>

      {/* Main chat area */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Mobile header */}
        <header className="flex items-center justify-between border-b bg-white px-4 py-3 lg:px-6">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">
              A
            </div>
            <span className="font-semibold text-gray-800">AarogyaAid Chat</span>
          </div>
          <button
            onClick={() => navigate('/recommendations')}
            className="text-xs text-brand-600 hover:underline"
          >
            ← Recommendations
          </button>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-5 lg:px-6">
          {/* Empty state with quick prompts */}
          {chatTurns.length === 0 && !loading && (
            <div className="flex flex-col items-center gap-6 pt-8">
              <div className="text-center">
                <p className="text-lg font-semibold text-gray-700">
                  {userProfile ? `Hello, ${userProfile.name}!` : 'Hello!'}
                </p>
                <p className="mt-1 text-sm text-gray-500">
                  Ask me anything about your health insurance plans.
                </p>
              </div>
              <div className="grid w-full max-w-lg gap-2 sm:grid-cols-2">
                {QUICK_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => send(prompt)}
                    className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-left text-sm text-gray-600 hover:border-brand-300 hover:bg-brand-50 transition-colors shadow-sm"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Chat turns */}
          {chatTurns.map((turn, i) => (
            <div key={i} className={`flex ${turn.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {turn.role === 'assistant' && (
                <div className="mr-2 mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">
                  A
                </div>
              )}

              <div className="max-w-[80%] min-w-0 lg:max-w-[70%]">
                <div
                  className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    turn.role === 'user'
                      ? 'bg-brand-600 text-white'
                      : turn.was_guardrailed
                      ? 'bg-amber-50 text-amber-900 ring-1 ring-amber-200'
                      : 'bg-white text-gray-800 shadow-sm ring-1 ring-gray-100'
                  }`}
                >
                  {turn.content}
                </div>

                {turn.role === 'assistant' && (
                  <div className="mt-1.5 space-y-1.5 px-1">
                    <div className="flex flex-wrap gap-1.5 items-center">
                      {turn.intent && !['greeting', 'unknown'].includes(turn.intent) && (
                        <IntentBadge intent={turn.intent} />
                      )}
                      {turn.was_guardrailed && (
                        <span className="text-xs text-amber-600">⚠ Redirected for your safety</span>
                      )}
                    </div>

                    {turn.cited_chunks && turn.cited_chunks.length > 0 && (
                      <CitationCard chunks={turn.cited_chunks} />
                    )}

                    {turn.grounding_warnings && turn.grounding_warnings.length > 0 && (
                      <p className="text-xs text-gray-400">
                        ⚠ {turn.grounding_warnings[0]}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {turn.role === 'user' && (
                <div className="ml-2 mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-200 text-xs font-bold text-gray-600">
                  {userProfile?.name?.[0]?.toUpperCase() ?? 'U'}
                </div>
              )}
            </div>
          ))}

          {loading && <TypingIndicator />}

          {error && (
            <Alert variant="error" className="mx-auto max-w-md">
              {error}
            </Alert>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div className="border-t bg-white px-4 py-3 lg:px-6">
          <div className="flex gap-3">
            <input
              ref={inputRef}
              type="text"
              className="flex-1 rounded-xl border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Ask about coverage, terms, claims…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send(input)}
              disabled={loading}
            />
            <Button
              onClick={() => send(input)}
              disabled={loading || !input.trim()}
              className="shrink-0"
            >
              {loading ? <Spinner size="sm" className="text-white" /> : 'Send'}
            </Button>
          </div>
          <p className="mt-2 text-center text-[11px] text-gray-400">
            Answers are grounded in uploaded policy documents. Not medical advice.
          </p>
        </div>
      </div>
    </div>
  )
}
