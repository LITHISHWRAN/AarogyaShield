import { useEffect, useState } from 'react'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Alert from '@/components/ui/Alert'
import Spinner from '@/components/ui/Spinner'
import Card from '@/components/ui/Card'
import AdminLogin from './AdminLogin'
import { adminPoliciesApi } from '@/services/api'
import { useAppStore } from '@/store'
import type { AdminPolicy, AdminUploadResponse } from '@/types'

export default function AdminPage() {
  const { adminToken, setAdminToken } = useAppStore()

  if (!adminToken) return <AdminLogin />

  return <AdminDashboard onLogout={() => setAdminToken(null)} />
}

function AdminDashboard({ onLogout }: { onLogout: () => void }) {
  const [policies, setPolicies] = useState<AdminPolicy[]>([])
  const [loadingPolicies, setLoadingPolicies] = useState(true)
  const [listError, setListError] = useState('')

  // Upload state
  const [file, setFile] = useState<File | null>(null)
  const [policyName, setPolicyName] = useState('')
  const [insurer, setInsurer] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<AdminUploadResponse | null>(null)
  const [uploadError, setUploadError] = useState('')

  // Delete state
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState('')

  const loadPolicies = async () => {
    setLoadingPolicies(true)
    setListError('')
    try {
      const res = await adminPoliciesApi.list()
      setPolicies(res.data)
    } catch {
      setListError('Failed to load policies. Check your session.')
    } finally {
      setLoadingPolicies(false)
    }
  }

  useEffect(() => { loadPolicies() }, [])

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !policyName.trim() || !insurer.trim()) return
    setUploadError('')
    setUploadResult(null)
    setUploading(true)
    try {
      const res = await adminPoliciesApi.upload(file, policyName.trim(), insurer.trim())
      setUploadResult(res.data)
      setFile(null)
      setPolicyName('')
      setInsurer('')
      await loadPolicies()
    } catch {
      setUploadError('Upload failed. Ensure the file is a valid PDF, TXT, or JSON.')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (policy_id: string) => {
    if (!window.confirm('Delete this policy and all its indexed vectors?')) return
    setDeletingId(policy_id)
    setDeleteError('')
    try {
      await adminPoliciesApi.delete(policy_id)
      await loadPolicies()
    } catch {
      setDeleteError('Delete failed. Please try again.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="border-b bg-white px-6 py-4">
        <div className="mx-auto max-w-5xl flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="AarogyaShield" className="h-8 w-8 object-contain" />
            <div>
              <h1 className="font-bold text-gray-900">Admin Dashboard</h1>
              <p className="text-sm text-gray-500">Policy document management</p>
            </div>
          </div>
          <Button variant="secondary" size="sm" onClick={onLogout}>
            Sign out
          </Button>
        </div>
      </div>

      <div className="mx-auto max-w-5xl px-4 py-8 space-y-8">

        {/* Upload */}
        <Card>
          <h2 className="mb-5 font-semibold text-gray-800">Upload policy document</h2>
          <form onSubmit={handleUpload} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                id="policy_name"
                label="Policy name *"
                placeholder="e.g. Star Health Optima Restore"
                required
                value={policyName}
                onChange={(e) => setPolicyName(e.target.value)}
              />
              <Input
                id="insurer"
                label="Insurer *"
                placeholder="e.g. Star Health Insurance"
                required
                value={insurer}
                onChange={(e) => setInsurer(e.target.value)}
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Document file * (PDF, TXT, or JSON)
              </label>
              <input
                type="file"
                accept=".pdf,.txt,.json"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="block w-full text-sm text-gray-600 file:mr-4 file:rounded-lg file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-brand-700 hover:file:bg-brand-100"
              />
            </div>

            {uploadError && <Alert variant="error">{uploadError}</Alert>}
            {uploadResult && (
              <Alert variant="success" title="Uploaded successfully">
                <p>Policy ID: <code className="text-xs">{uploadResult.policy_id}</code></p>
                <p>{uploadResult.chunks_indexed} chunks indexed from {uploadResult.filename}</p>
              </Alert>
            )}

            <Button
              type="submit"
              disabled={!file || !policyName.trim() || !insurer.trim() || uploading}
            >
              {uploading ? (
                <span className="flex items-center gap-2">
                  <Spinner size="sm" className="text-white" />
                  Indexing…
                </span>
              ) : (
                'Upload & Index'
              )}
            </Button>
          </form>
        </Card>

        {/* Policy list */}
        <Card padding="sm">
          <div className="px-2 py-3 flex items-center justify-between">
            <h2 className="font-semibold text-gray-800">Indexed policies</h2>
            <Button variant="secondary" size="sm" onClick={loadPolicies} disabled={loadingPolicies}>
              Refresh
            </Button>
          </div>

          {deleteError && <Alert variant="error" className="mx-2 mb-3">{deleteError}</Alert>}

          {loadingPolicies ? (
            <div className="flex justify-center py-10">
              <Spinner size="lg" />
            </div>
          ) : listError ? (
            <Alert variant="error" className="m-2">{listError}</Alert>
          ) : policies.length === 0 ? (
            <p className="px-4 py-10 text-center text-sm text-gray-400">
              No policies indexed yet. Upload a document above.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs font-semibold uppercase tracking-wide text-gray-400">
                    <th className="px-4 py-3">Policy name</th>
                    <th className="px-4 py-3">Insurer</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3 text-right">Chunks</th>
                    <th className="px-4 py-3 text-right">Uploaded</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {policies.map((p) => (
                    <tr key={p.policy_id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-800">{p.policy_name}</td>
                      <td className="px-4 py-3 text-gray-600">{p.insurer}</td>
                      <td className="px-4 py-3">
                        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium uppercase text-gray-500">
                          {p.file_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-gray-600">{p.chunk_count}</td>
                      <td className="px-4 py-3 text-right text-xs text-gray-400">
                        {new Date(p.upload_date).toLocaleDateString('en-IN')}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          variant="danger"
                          size="sm"
                          disabled={deletingId === p.policy_id}
                          onClick={() => handleDelete(p.policy_id)}
                        >
                          {deletingId === p.policy_id ? (
                            <Spinner size="sm" className="text-white" />
                          ) : (
                            'Delete'
                          )}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <p className="text-center text-xs text-gray-400">
          Deleting a policy immediately removes all its vectors from Qdrant.
          This cannot be undone.
        </p>
      </div>
    </div>
  )
}
