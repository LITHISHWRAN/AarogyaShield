import { Route, Routes } from 'react-router-dom'
import AdminPage from '@/features/admin/AdminPage'
import ChatPage from '@/features/chat/ChatPage'
import OnboardingPage from '@/features/onboarding/OnboardingPage'
import PoliciesPage from '@/features/policies/PoliciesPage'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <Routes>
        <Route path="/" element={<OnboardingPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/policies" element={<PoliciesPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </div>
  )
}
