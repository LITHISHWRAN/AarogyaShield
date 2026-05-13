import { Route, Routes } from 'react-router-dom'
import AdminPage from '@/features/admin/AdminPage'
import ChatPage from '@/features/chat/ChatPage'
import OnboardingPage from '@/features/onboarding/OnboardingPage'
import RecommendationsPage from '@/features/recommendations/RecommendationsPage'
import DashboardPage from '@/features/dashboard/DashboardPage'

export default function App() {
  return (
    // <div className="min-h-screen bg-gray-50 text-gray-900">
      <Routes>
        <Route path="/" element={<OnboardingPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        {/* Legacy routes kept as fallback */}
        <Route path="/recommendations" element={<RecommendationsPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    // </div>
  )
}
