import { useEffect, useRef, useState } from 'react'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { chatApi } from '@/services/api'
import { useAppStore } from '@/store'

export default function ChatPage() {
  const { sessionId, userProfile, chatHistory, addMessage } = useAppStore()
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory])

  const send = async () => {
    if (!input.trim() || loading) return
    const text = input.trim()
    addMessage({ role: 'user', content: text })
    setInput('')
    setLoading(true)
    try {
      const res = await chatApi.send(sessionId, text, userProfile ?? undefined)
      addMessage({ role: 'assistant', content: res.data.reply })
    } catch {
      addMessage({ role: 'assistant', content: 'Something went wrong. Please try again.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen flex-col">
      <header className="border-b bg-white px-6 py-4">
        <h1 className="text-lg font-semibold text-brand-700">AarogyaShield Chat</h1>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {chatHistory.length === 0 && (
          <p className="mt-16 text-center text-sm text-gray-400">
            Ask me anything about health insurance policies.
          </p>
        )}
        {chatHistory.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === 'user'
                  ? 'bg-brand-600 text-white'
                  : 'bg-white text-gray-800 shadow'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-white px-4 py-3 text-sm text-gray-400 shadow">
              Thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t bg-white px-6 py-4 flex gap-3">
        <Input
          className="flex-1"
          placeholder="Ask about a policy, coverage, or premium…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
        />
        <Button onClick={send} disabled={loading || !input.trim()}>
          Send
        </Button>
      </div>
    </div>
  )
}
