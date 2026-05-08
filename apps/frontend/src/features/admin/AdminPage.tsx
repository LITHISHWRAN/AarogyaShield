import { useState } from 'react'
import Button from '@/components/ui/Button'
import { adminApi } from '@/services/api'

export default function AdminPage() {
  const [file, setFile] = useState<File | null>(null)
  const [deleteId, setDeleteId] = useState('')
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)

  const handleUpload = async () => {
    if (!file) return
    setBusy(true)
    setStatus('Uploading…')
    try {
      const res = await adminApi.upload(file)
      setStatus(
        `Indexed ${res.data.chunks_indexed} chunks — policy ID: ${res.data.policy_id}`,
      )
      setFile(null)
    } catch {
      setStatus('Upload failed. Check that the file is a valid PDF.')
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteId.trim()) return
    setBusy(true)
    setStatus('Deleting…')
    try {
      const res = await adminApi.delete(deleteId.trim())
      setStatus(`Deleted policy ${res.data.policy_id}. Vectors removed: ${res.data.vectors_removed}`)
      setDeleteId('')
    } catch {
      setStatus('Delete failed. Verify the policy ID.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl p-6">
      <h1 className="mb-6 text-2xl font-bold text-brand-700">Admin Panel</h1>

      <section className="mb-6 rounded-xl bg-white p-6 shadow">
        <h2 className="mb-4 font-semibold text-gray-800">Upload Policy PDF</h2>
        <input
          type="file"
          accept=".pdf"
          className="mb-4 block text-sm text-gray-600"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <Button onClick={handleUpload} disabled={!file || busy}>
          Upload & Index
        </Button>
      </section>

      <section className="mb-6 rounded-xl bg-white p-6 shadow">
        <h2 className="mb-4 font-semibold text-gray-800">Delete Policy</h2>
        <input
          type="text"
          placeholder="Policy ID"
          value={deleteId}
          onChange={(e) => setDeleteId(e.target.value)}
          className="mb-4 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <Button variant="danger" onClick={handleDelete} disabled={!deleteId.trim() || busy}>
          Delete Policy & Vectors
        </Button>
      </section>

      {status && (
        <p className="rounded-lg bg-gray-100 p-3 text-sm text-gray-700">{status}</p>
      )}
    </div>
  )
}
