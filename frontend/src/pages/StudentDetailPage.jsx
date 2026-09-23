import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ScanFace, Trash2 } from 'lucide-react'
import { api, normalizeError } from '../lib/api.js'
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  PageHeader,
  PageLoader,
  Spinner,
  StatusBadge,
} from '../components/ui.jsx'
import FileUpload from '../components/FileUpload.jsx'

export default function StudentDetailPage() {
  const { id } = useParams()
  const [student, setStudent] = useState(null)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [flash, setFlash] = useState('')

  const load = useCallback(() => {
    setError('')
    api
      .get(`/students/${id}/`)
      .then((r) => setStudent(r.data))
      .catch((err) => setError(normalizeError(err)))
    api
      .get(`/students/${id}/face-status/`)
      .then((r) => setStatus(r.data))
      .catch(() => {})
  }, [id])

  useEffect(load, [load])

  const uploadPhoto = async (file) => {
    setUploading(true)
    setFlash('')
    const body = new FormData()
    body.append('image', file)
    try {
      await api.post(`/students/${id}/face-registration/`, body)
      setFlash('Photo processed and face embedding updated.')
      load()
    } catch (err) {
      setError(normalizeError(err))
    } finally {
      setUploading(false)
    }
  }

  const clearFaces = async () => {
    if (!window.confirm('Remove all face photos and the face registration for this student?')) return
    setBusy(true)
    setFlash('')
    try {
      await api.delete(`/students/${id}/face-registration/`)
      setFlash('Face registration removed.')
      load()
    } catch (err) {
      setError(normalizeError(err))
    } finally {
      setBusy(false)
    }
  }

  if (error && !student) return <Alert>{error}</Alert>
  if (!student) return <PageLoader label="Loading student…" />

  const photos = status?.photos || []
  const maxPhotos = status?.max_photos || 5

  return (
    <div>
      <Link to="/students" className="mb-4 inline-flex items-center gap-1 text-sm text-brand-600 hover:underline">
        <ArrowLeft className="h-4 w-4" /> Back to students
      </Link>

      <PageHeader title={student.full_name} subtitle={`${student.roll_number} · ${student.student_id}`} />

      {error && <div className="mb-4"><Alert>{error}</Alert></div>}
      {flash && <div className="mb-4"><Alert variant="success">{flash}</Alert></div>}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="p-6 lg:col-span-2">
          <h2 className="mb-4 text-base font-semibold text-slate-800">Profile</h2>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {[
              ['Class', `${student.class_name} — ${student.division_name}`],
              ['Student ID', student.student_id],
              ['Roll number', student.roll_number],
              ['Email', student.email || '—'],
              ['Mobile', student.mobile || '—'],
              [
                'Gender',
                student.gender ? student.gender.charAt(0).toUpperCase() + student.gender.slice(1) : '—',
              ],
              ['Date of birth', student.date_of_birth || '—'],
              ['Academic year', student.academic_year || '—'],
              ['Status', <StatusBadge key="s" status={student.status} />],
              [
                'Face registration',
                student.face_registered ? <Badge key="f" color="green">Registered</Badge> : <Badge key="f2" color="amber">Pending</Badge>,
              ],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</dt>
                <dd className="mt-0.5 text-sm text-slate-800">{value}</dd>
              </div>
            ))}
          </dl>
        </Card>

        <Card className="p-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-base font-semibold text-slate-800">
              <ScanFace className="h-4 w-4 text-brand-500" /> Face data
            </h2>
            {photos.length > 0 && (
              <Button variant="danger" size="" onClick={clearFaces} disabled={busy}>
                <Trash2 className="h-4 w-4" /> {busy ? <Spinner /> : 'Remove'}
              </Button>
            )}
          </div>

          <p className="mb-4 text-xs text-slate-400">
            {status?.face_registered
              ? `Face registered · ${photos.length}/${maxPhotos} photo(s) on file`
              : `Not registered · ${photos.length}/${maxPhotos} photo(s) on file`}
          </p>

          {photos.length > 0 && (
            <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
              {photos.map((p) => (
                <div key={p.id} className="aspect-square overflow-hidden rounded-lg border border-slate-200 bg-slate-100">
                  <img src={p.image} alt="Student face" className="h-full w-full object-cover" />
                </div>
              ))}
              {Array.from({ length: maxPhotos - photos.length }).map((_, i) => (
                <FileUpload key={`empty-${i}`} compact onSelect={uploadPhoto} loading={uploading} />
              ))}
            </div>
          )}

          {photos.length === 0 && <FileUpload onSelect={uploadPhoto} loading={uploading} />}

          {status?.face_registered && (
            <p className="mt-4 rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-700">
              Embedding model: {student.embedding_dim} dimensions. Attendance recognition will match this face automatically.
            </p>
          )}
        </Card>
      </div>
    </div>
  )
}