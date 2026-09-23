import { useEffect, useState } from 'react'
import { api, normalizeError, unwrapList } from '../lib/api.js'
import { Alert, Button, Field, Input, Select, Spinner } from './ui.jsx'

function todayISO() {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

/**
 * Shared "new attendance session" form (class -> division, subject, date,
 * lecture). Used by the Attendance page modal and the Mark Attendance module.
 *
 * `classroom`, `division` and `subject` must all belong together - the API
 * rejects mismatched triples - so subject and division options are refetched
 * whenever the class changes.
 */
export default function SessionForm({ onCreated, onCancel, submitLabel = 'Create session' }) {
  const [classrooms, setClassrooms] = useState([])
  const [divisions, setDivisions] = useState([])
  const [subjects, setSubjects] = useState([])
  const [form, setForm] = useState({
    classroom: '',
    division: '',
    subject: '',
    date: todayISO(),
    lecture_number: '',
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api
      .get('/classes/classrooms/')
      .then((r) => setClassrooms(unwrapList(r)))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!form.classroom) {
      setDivisions([])
      setSubjects([])
      return
    }
    api
      .get('/classes/divisions/', { params: { classroom: form.classroom } })
      .then((r) => setDivisions(unwrapList(r)))
      .catch(() => {})
    api
      .get('/classes/subjects/', { params: { classroom: form.classroom } })
      .then((r) => setSubjects(unwrapList(r)))
      .catch(() => {})
  }, [form.classroom])

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      const payload = {
        classroom: Number(form.classroom),
        division: Number(form.division),
        subject: Number(form.subject),
        date: form.date,
      }
      const lecture = form.lecture_number.trim()
      if (lecture) payload.lecture_number = lecture
      const r = await api.post('/attendance/sessions/', payload)
      onCreated?.(r.data)
    } catch (err) {
      setError(normalizeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      {error && <Alert>{error}</Alert>}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Class" required>
          <Select value={form.classroom} onChange={(e) => setForm((f) => ({ ...f, classroom: e.target.value, division: '', subject: '' }))}>
            <option value="">Select a class</option>
            {classrooms.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.academic_year})
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Division" required>
          <Select value={form.division} onChange={set('division')} disabled={!form.classroom}>
            <option value="">{form.classroom ? 'Select a division' : 'Pick a class first'}</option>
            {divisions.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Subject" required>
          <Select value={form.subject} onChange={set('subject')} disabled={!form.classroom}>
            <option value="">{form.classroom ? 'Select a subject' : 'Pick a class first'}</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Date" required>
          <Input type="date" value={form.date} onChange={set('date')} />
        </Field>
        <div className="sm:col-span-2">
          <Field label="Lecture number" hint="Optional - e.g. L1, Lecture 3">
            <Input placeholder="L1" value={form.lecture_number} onChange={set('lecture_number')} />
          </Field>
        </div>
      </div>
      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button type="button" variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={saving || !form.classroom || !form.division || !form.subject}>
          {saving ? <Spinner /> : submitLabel}
        </Button>
      </div>
    </form>
  )
}
