import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Camera, ChevronLeft, ChevronRight, Plus, Search, Trash2 } from 'lucide-react'
import { api, normalizeError, unwrapList } from '../lib/api.js'
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  Modal,
  PageHeader,
  Select,
  Spinner,
  StatusBadge,
  Td,
  Th,
} from '../components/ui.jsx'
import CameraCapture from '../components/CameraCapture.jsx'
import FileUpload from '../components/FileUpload.jsx'

const MAX_PHOTOS = 3 // keep in sync with backend settings.MAX_STUDENT_PHOTOS
const MAX_SIZE_MB = 10

export default function StudentsPage() {
  const [classrooms, setClassrooms] = useState([])
  const [allDivisions, setAllDivisions] = useState([])
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [page, setPage] = useState(1)
  const [count, setCount] = useState(0)
  const [search, setSearch] = useState('')
  const [divisionFilter, setDivisionFilter] = useState('')

  const [studentModal, setStudentModal] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [form, setForm] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const [notice, setNotice] = useState(null)
  const [photos, setPhotos] = useState([])
  const [canAddPhotos, setCanAddPhotos] = useState(false)
  const [showCamera, setShowCamera] = useState(false)
  const [stage, setStage] = useState('')

  useEffect(() => {
    api.get('/classes/classrooms/').then((r) => setClassrooms(unwrapList(r))).catch(() => {})
    api.get('/classes/divisions/').then((r) => setAllDivisions(unwrapList(r))).catch(() => {})
  }, [])

  const load = (opts = {}) => {
    setLoading(true)
    setError('')
    const params = {}
    if (opts.search ?? search) params.search = opts.search ?? search
    if (opts.division ?? divisionFilter) params.division = opts.division ?? divisionFilter
    params.page = opts.page ?? page
    api
      .get('/students/', { params })
      .then((r) => {
        setStudents(r.data.results)
        setCount(r.data.count)
      })
      .catch((err) => setError(normalizeError(err)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  const pages = useMemo(() => Math.max(1, Math.ceil(count / 20)), [count])

  const clearPhotos = () => {
    photos.forEach((p) => URL.revokeObjectURL(p.url))
    setPhotos([])
    setShowCamera(false)
    setStage('')
  }

  const closeModal = () => {
    setStudentModal(false)
    clearPhotos()
  }

  const addPhotos = (files) => {
    const list = Array.isArray(files) ? files : [files]
    const messages = []
    const additions = []

    for (const file of list) {
      if (!file.type?.startsWith('image/')) {
        messages.push(`"${file.name}" is not an image`)
        continue
      }
      if (file.size > MAX_SIZE_MB * 1024 * 1024) {
        messages.push(`"${file.name}" is larger than ${MAX_SIZE_MB} MB`)
        continue
      }
      if (photos.length + additions.length >= MAX_PHOTOS) {
        messages.push(`Only ${MAX_PHOTOS} photos per student`)
        break
      }
      additions.push({
        key: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        file,
        url: URL.createObjectURL(file),
        status: 'pending',
        message: '',
      })
    }

    if (messages.length) setFormError(messages.join('. '))
    if (additions.length) setPhotos((prev) => [...prev, ...additions])
    setShowCamera(false)
  }

  const removePhoto = (key) => {
    setPhotos((prev) => {
      const target = prev.find((p) => p.key === key)
      if (target) URL.revokeObjectURL(target.url)
      return prev.filter((p) => p.key !== key)
    })
  }

  const openCreate = () => {
    setFormError('')
    setNotice(null)
    clearPhotos()
    setCanAddPhotos(true)
    setForm({
      full_name: '',
      roll_number: '',
      student_id: '',
      email: '',
      mobile: '',
      gender: '',
      date_of_birth: '',
      academic_year: '',
      status: 'active',
      division: '',
      id: undefined,
    })
    setStudentModal(true)
  }

  const saveStudent = async (e) => {
    e.preventDefault()
    setFormError('')
    setNotice(null)
    setSaving(true)
    const isEdit = Boolean(form.id)
    let studentId = form.id

    try {
      const payload = { ...form }
      payload.division = Number(payload.division)
      if (payload.gender === '') delete payload.gender
      if (payload.date_of_birth === '') delete payload.date_of_birth
      if (payload.email === '') delete payload.email
      if (payload.mobile === '') delete payload.mobile

      if (isEdit) {
        setStage('Saving…')
        await api.patch(`/students/${studentId}/`, payload)
      } else {
        setStage('Creating student…')
        const r = await api.post('/students/', payload)
        studentId = r.data?.id
      }

      // Register face photos so AI attendance works straight away.
      const pending = photos.filter((p) => p.status === 'pending')
      const failures = []
      let registered = 0
      for (let i = 0; i < pending.length; i += 1) {
        const photo = pending[i]
        setStage(`Processing photo ${i + 1} of ${pending.length}…`)
        setPhotos((prev) => prev.map((p) => (p.key === photo.key ? { ...p, status: 'uploading' } : p)))
        try {
          const body = new FormData()
          body.append('image', photo.file, photo.file.name || 'photo.jpg')
          await api.post(`/students/${studentId}/face-registration/`, body)
          registered += 1
          setPhotos((prev) => prev.map((p) => (p.key === photo.key ? { ...p, status: 'ok' } : p)))
        } catch (err) {
          const msg = normalizeError(err)
          failures.push(`"${photo.file.name}": ${msg}`)
          setPhotos((prev) => prev.map((p) => (p.key === photo.key ? { ...p, status: 'error', message: msg } : p)))
        }
      }

      closeModal()
      load(page)

      if (failures.length) {
        setNotice({
          variant: 'warning',
          text: `${isEdit ? 'Changes saved' : 'Student added'}${registered ? ` · ${registered} photo(s) registered` : ''}, but ${failures.length} photo(s) were rejected: ${failures.join(' · ')}`,
        })
      } else if (registered) {
        setNotice({
          variant: 'success',
          text: `${isEdit ? 'Changes saved' : 'Student added'} with ${registered} face photo(s) — AI attendance is ready.`,
        })
      } else {
        setNotice({ variant: 'info', text: `${isEdit ? 'Changes saved' : 'Student added'}.` })
      }
    } catch (err) {
      setFormError(normalizeError(err))
    } finally {
      setSaving(false)
      setStage('')
    }
  }

  const removeStudent = async (id, name) => {
    if (!window.confirm(`Delete student “${name}”? Attendance history will be kept but the profile is removed.`)) return
    setDeletingId(id)
    try {
      await api.delete(`/students/${id}/`)
      load(page)
    } catch (err) {
      window.alert(normalizeError(err))
    } finally {
      setDeletingId(null)
    }
  }

  const applyFilters = () => {
    setPage(1)
    load({ page: 1 })
  }

  const filterRow = (
    <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-4">
      <div className="relative sm:col-span-2">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          className="pl-9"
          placeholder="Search by name, roll number or PRN…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && applyFilters()}
        />
      </div>
      <Select value={divisionFilter} onChange={(e) => setDivisionFilter(e.target.value)}>
        <option value="">All divisions</option>
        {classrooms.map((c) => (
          <optgroup key={c.id} label={`${c.name} (${c.academic_year})`}>
            {allDivisions
              .filter((d) => Number(d.classroom) === c.id)
              .map((d) => (
                <option key={d.id} value={d.id}>
                  {c.name} — {d.name}
                </option>
              ))}
          </optgroup>
        ))}
      </Select>
      <Button onClick={applyFilters}>Apply</Button>
    </div>
  )

  return (
    <div>
      <PageHeader
        title="Students"
        subtitle={`${count} registered student(s)`}
        actions={
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" />
            Add student
          </Button>
        }
      />

      {error && <div className="mb-4"><Alert>{error}</Alert></div>}
      {notice && (
        <div className="mb-4">
          <Alert variant={notice.variant}>{notice.text}</Alert>
        </div>
      )}

      {filterRow}

      <Card>
        {loading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : students.length === 0 ? (
          <EmptyState title="No students found" hint="Add students or adjust the search filters" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <Th>Name</Th>
                  <Th>Roll</Th>
                  <Th>Student ID</Th>
                  <Th>Class</Th>
                  <Th>Face</Th>
                  <Th>Status</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {students.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50">
                    <Td className="font-medium text-slate-900">{s.full_name}</Td>
                    <Td>{s.roll_number}</Td>
                    <Td>{s.student_id}</Td>
                    <Td>
                      {s.class_name} — {s.division_name}
                    </Td>
                    <Td>
                      {s.face_registered ? (
                        <Badge color="green">Registered ({s.photo_count})</Badge>
                      ) : (
                        <Badge color="amber">Pending</Badge>
                      )}
                    </Td>
                    <Td><StatusBadge status={s.status} /></Td>
                    <Td className="text-right">
                      <Link
                        to={`/students/${s.id}`}
                        className="rounded-lg px-2 py-1 text-sm text-brand-600 hover:bg-brand-50"
                      >
                        View
                      </Link>
                      <Button
                        variant="ghost"
                        onClick={() => {
                          setFormError('')
                          setNotice(null)
                          clearPhotos()
                          // Photos can be added here only while no face is enrolled
                          // (the detail page manages an existing registration).
                          setCanAddPhotos(!s.face_registered)
                          setForm({
                            full_name: s.full_name,
                            roll_number: s.roll_number,
                            student_id: s.student_id,
                            email: s.email || '',
                            mobile: s.mobile || '',
                            gender: s.gender || '',
                            date_of_birth: s.date_of_birth || '',
                            academic_year: s.academic_year || '',
                            status: s.status,
                            division: s.division,
                            id: s.id,
                          })
                          setStudentModal(true)
                        }}
                      >
                        Edit
                      </Button>
                      <Button variant="ghost" onClick={() => removeStudent(s.id, s.full_name)} disabled={deletingId === s.id}>
                        Delete
                      </Button>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {pages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <Button variant="secondary" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
            <ChevronLeft className="h-4 w-4" /> Previous
          </Button>
          <span className="text-sm text-slate-500">
            Page {page} of {pages}
          </span>
          <Button variant="secondary" onClick={() => setPage((p) => Math.min(pages, p + 1))} disabled={page >= pages}>
            Next <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      <Modal
        open={studentModal}
        onClose={closeModal}
        title={form.id ? 'Edit student' : 'Add student'}
        wide
      >
        <form onSubmit={saveStudent} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {formError && <div className="sm:col-span-2"><Alert>{formError}</Alert></div>}
          <Field label="Full name" required>
            <Input value={form.full_name} onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))} />
          </Field>
          <Field label="Roll number" required>
            <Input value={form.roll_number} onChange={(e) => setForm((f) => ({ ...f, roll_number: e.target.value }))} />
          </Field>
          <Field label="Student ID / PRN" required>
            <Input value={form.student_id} onChange={(e) => setForm((f) => ({ ...f, student_id: e.target.value }))} />
          </Field>
          <Field label="Academic year">
            <Input placeholder="2026-2027" value={form.academic_year} onChange={(e) => setForm((f) => ({ ...f, academic_year: e.target.value }))} />
          </Field>
          <div className="sm:col-span-2">
            <Field label="Division" required>
              <Select value={form.division} onChange={(e) => setForm((f) => ({ ...f, division: e.target.value }))}>
                <option value="">Select a division</option>
                {classrooms.map((c) => (
                  <optgroup key={c.id} label={`${c.name} (${c.academic_year})`}>
                    {allDivisions
                      .filter((d) => Number(d.classroom) === c.id)
                      .map((d) => (
                        <option key={d.id} value={d.id}>
                          {c.name} — {d.name}
                        </option>
                      ))}
                  </optgroup>
                ))}
              </Select>
            </Field>
          </div>
          <Field label="Email">
            <Input type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
          </Field>
          <Field label="Mobile">
            <Input value={form.mobile} onChange={(e) => setForm((f) => ({ ...f, mobile: e.target.value }))} />
          </Field>
          <Field label="Gender">
            <Select value={form.gender} onChange={(e) => setForm((f) => ({ ...f, gender: e.target.value }))}>
              <option value="">Not specified</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </Select>
          </Field>
          <Field label="Date of birth">
            <Input type="date" value={form.date_of_birth} onChange={(e) => setForm((f) => ({ ...f, date_of_birth: e.target.value }))} />
          </Field>
          <Field label="Status">
            <Select value={form.status} onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="transferred">Transferred</option>
            </Select>
          </Field>

          {canAddPhotos && (
            <div className="sm:col-span-2 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-700">
                Face photo {form.id ? '' : '(for AI attendance)'}
              </p>
              <p className="mb-3 text-xs text-slate-400">
                Clear, front-facing photos — one face per photo, no blur or sunglasses. Up to{' '}
                {MAX_PHOTOS} photos; the AI needs at least one to recognize this student.
              </p>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <FileUpload
                  compact
                  multiple
                  maxFiles={MAX_PHOTOS - photos.length}
                  onSelect={addPhotos}
                  loading={saving}
                  disabled={saving || photos.length >= MAX_PHOTOS}
                  hint={`JPG / PNG · max ${MAX_SIZE_MB} MB · ${photos.length}/${MAX_PHOTOS} selected`}
                  label="Upload face photos"
                />
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => setShowCamera((v) => !v)}
                    disabled={saving || photos.length >= MAX_PHOTOS}
                    className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                  >
                    <Camera className="h-4 w-4" />
                    {showCamera ? 'Hide camera' : 'Take a photo with camera'}
                  </button>
                  {showCamera && (
                    <CameraCapture
                      compact
                      label="Capture photo"
                      capturing={saving}
                      disabled={saving}
                      onCapture={(blob) =>
                        addPhotos([new File([blob], `capture-${Date.now()}.jpg`, { type: 'image/jpeg' })])
                      }
                    />
                  )}
                </div>
              </div>

              {photos.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-3">
                  {photos.map((p) => (
                    <div
                      key={p.key}
                      className="relative h-24 w-24 overflow-hidden rounded-lg border border-slate-200 bg-white"
                    >
                      <img src={p.url} alt="" className="h-full w-full object-cover" />
                      <span
                        className={[
                          'absolute bottom-0 left-0 right-0 px-1 py-0.5 text-center text-[10px] font-medium text-white',
                          p.status === 'ok'
                            ? 'bg-emerald-600/90'
                            : p.status === 'error'
                              ? 'bg-rose-600/90'
                              : p.status === 'uploading'
                                ? 'bg-brand-600/90'
                                : 'bg-slate-700/80',
                        ].join(' ')}
                        title={p.message || undefined}
                      >
                        {p.status === 'ok'
                          ? 'Registered'
                          : p.status === 'error'
                            ? 'Rejected'
                            : p.status === 'uploading'
                              ? 'Processing…'
                              : 'Ready'}
                      </span>
                      <button
                        type="button"
                        onClick={() => removePhoto(p.key)}
                        disabled={saving}
                        aria-label="Remove photo"
                        className="absolute right-1 top-1 rounded-md bg-slate-900/60 p-1 text-white hover:bg-slate-900 disabled:opacity-40"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              {photos.some((p) => p.status === 'error') && (
                <ul className="mt-2 space-y-1">
                  {photos
                    .filter((p) => p.status === 'error')
                    .map((p) => (
                      <li key={p.key} className="text-xs text-rose-600">
                        "{p.file.name}" — {p.message}
                      </li>
                    ))}
                </ul>
              )}
            </div>
          )}

          <div className="sm:col-span-2 flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={closeModal} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? (
                <>
                  <Spinner /> {stage || 'Saving…'}
                </>
              ) : form.id ? (
                photos.length ? 'Save & register photo(s)' : 'Save changes'
              ) : photos.length ? (
                'Add student & register photo(s)'
              ) : (
                'Add student'
              )}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}