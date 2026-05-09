import { Route, Routes } from 'react-router-dom'
import AdminPage from '@/features/admin/AdminPage'
import ChatPage from '@/features/chat/ChatPage'
import OnboardingPage from '@/features/onboarding/OnboardingPage'
import RecommendationsPage from '@/features/recommendations/RecommendationsPage'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <Routes>
        <Route path="/" element={<OnboardingPage />} />
        <Route path="/recommendations" element={<RecommendationsPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </div>
  )
}
