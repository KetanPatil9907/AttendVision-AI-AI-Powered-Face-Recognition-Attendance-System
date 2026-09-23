import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
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
  Td,
  Th,
} from '../components/ui.jsx'

function useLoad(fetcher, deps = []) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    setLoading(true)
    fetcher()
      .then((r) => setData(unwrapList(r)))
      .catch((err) => setError(normalizeError(err)))
      .finally(() => setLoading(false))
  }, deps)
  return { data, setData, loading, error }
}

export default function ClassesPage() {
  const [tab, setTab] = useState('classrooms')
  const classrooms = useLoad(() => api.get('/classes/classrooms/'))
  const divisions = useLoad(() => api.get('/classes/divisions/'))
  const subjects = useLoad(() => api.get('/classes/subjects/'))

  const [modal, setModal] = useState(null)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [form, setForm] = useState({})

  const tabs = [
    { key: 'classrooms', label: 'Classes', count: classrooms.data.length },
    { key: 'divisions', label: 'Divisions', count: divisions.data.length },
    { key: 'subjects', label: 'Subjects', count: subjects.data.length },
  ]

  const openCreate = (kind) => {
    setFormError('')
    setForm(
      kind === 'classroom'
        ? { name: '', code: '', academic_year: '', description: '', id: undefined }
        : { classroom: '', name: '', code: '', id: undefined },
    )
    setModal(kind)
  }

  const save = async (e) => {
    e.preventDefault()
    setFormError('')
    setSaving(true)
    const kind = modal // 'classroom' | 'division' | 'subject' (singular)
    const plural = kind === 'classroom' ? 'classrooms' : kind === 'division' ? 'divisions' : 'subjects'
    const url = `/classes/${plural}/`
    const reload = {
      classrooms: () => api.get('/classes/classrooms/').then((r) => classrooms.setData(unwrapList(r))),
      divisions: () => api.get('/classes/divisions/').then((r) => divisions.setData(unwrapList(r))),
      subjects: () => api.get('/classes/subjects/').then((r) => subjects.setData(unwrapList(r))),
    }
    try {
      if (form.id) {
        await api.patch(`${url}${form.id}/`, form)
      } else {
        await api.post(url, form)
      }
      await reload[plural]()
      if (kind === 'classroom') {
        // Class names appear in the division and subject tables too.
        await Promise.all([reload.divisions(), reload.subjects()])
      }
      setModal(null)
    } catch (err) {
      setFormError(normalizeError(err))
    } finally {
      setSaving(false)
    }
  }

  const remove = async (kind, id, label) => {
    if (!window.confirm(`Delete ${label}? Related students or sessions will also be affected.`)) return
    const plural = kind === 'classroom' ? 'classrooms' : kind === 'division' ? 'divisions' : 'subjects'
    const url = `/classes/${plural}/${id}/`
    try {
      await api.delete(url)
      if (plural === 'classrooms') {
        await Promise.all([
          api.get('/classes/classrooms/').then((r) => classrooms.setData(unwrapList(r))),
          api.get('/classes/divisions/').then((r) => divisions.setData(unwrapList(r))),
          api.get('/classes/subjects/').then((r) => subjects.setData(unwrapList(r))),
        ])
      } else if (plural === 'subjects') {
        await api.get('/classes/subjects/').then((r) => subjects.setData(unwrapList(r)))
      } else {
        await api.get('/classes/divisions/').then((r) => divisions.setData(unwrapList(r)))
      }
    } catch (err) {
      window.alert(normalizeError(err))
    }
  }

  return (
    <div>
      <PageHeader
        title="Classes"
        subtitle="Manage classes, divisions and subjects"
        actions={
          <Button onClick={() => openCreate(tab === 'classrooms' ? 'classroom' : tab === 'divisions' ? 'division' : 'subject')}>
            <Plus className="h-4 w-4" />
            Add {tab === 'classrooms' ? 'class' : tab === 'divisions' ? 'division' : 'subject'}
          </Button>
        }
      />

      <div className="mb-4 flex gap-2">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
            }`}
          >
            {t.label} <span className="opacity-60">({t.count})</span>
          </button>
        ))}
      </div>

      <Card>
        {(tab === 'classrooms' ? classrooms : tab === 'divisions' ? divisions : subjects).loading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : (tab === 'classrooms' ? classrooms : tab === 'divisions' ? divisions : subjects).data.length === 0 ? (
          <EmptyState title={`No ${tab} yet`} hint="Add your first record using the button above" />
        ) : tab === 'classrooms' ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <Th>Class</Th>
                  <Th>Code</Th>
                  <Th>Academic year</Th>
                  <Th>Divisions</Th>
                  <Th>Subjects</Th>
                  <Th>Students</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {classrooms.data.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <Td className="font-medium text-slate-900">{c.name}</Td>
                    <Td>{c.code || '—'}</Td>
                    <Td>{c.academic_year}</Td>
                    <Td><Badge>{c.division_count}</Badge></Td>
                    <Td><Badge color="blue">{c.subject_count}</Badge></Td>
                    <Td><Badge color="green">{c.student_count}</Badge></Td>
                    <Td className="text-right">
                      <Button
                        variant="ghost"
                        onClick={() => {
                          setFormError('')
                          setForm({
                            name: c.name,
                            code: c.code || '',
                            academic_year: c.academic_year,
                            description: c.description || '',
                            id: c.id,
                          })
                          setModal('classroom')
                        }}
                      >
                        Edit
                      </Button>
                      <Button variant="ghost" onClick={() => remove('classroom', c.id, c.name)}>
                        Delete
                      </Button>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : tab === 'divisions' ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <Th>Division</Th>
                  <Th>Class</Th>
                  <Th>Academic year</Th>
                  <Th>Students</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {divisions.data.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50">
                    <Td className="font-medium text-slate-900">{d.name}</Td>
                    <Td>{d.class_name}</Td>
                    <Td>{d.academic_year}</Td>
                    <Td><Badge color="green">{d.student_count}</Badge></Td>
                    <Td className="text-right">
                      <Button variant="ghost" onClick={() => remove('division', d.id, d.name)}>
                        Delete
                      </Button>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <Th>Subject</Th>
                  <Th>Code</Th>
                  <Th>Class</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {subjects.data.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50">
                    <Td className="font-medium text-slate-900">{s.name}</Td>
                    <Td>{s.code || '—'}</Td>
                    <Td>{s.class_name}</Td>
                    <Td className="text-right">
                      <Button variant="ghost" onClick={() => remove('subject', s.id, s.name)}>
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

      <Modal
        open={!!modal}
        onClose={() => setModal(null)}
        title={form.id ? 'Edit record' : `Add ${modal === 'classroom' ? 'class' : modal === 'division' ? 'division' : 'subject'}`}
      >
        <form onSubmit={save} className="space-y-4">
          {formError && <Alert>{formError}</Alert>}
          {modal === 'classroom' ? (
            <>
              <Field label="Class name" required>
                <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Code">
                  <Input value={form.code} onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))} />
                </Field>
                <Field label="Academic year" required>
                  <Input
                    placeholder="2026-2027"
                    value={form.academic_year}
                    onChange={(e) => setForm((f) => ({ ...f, academic_year: e.target.value }))}
                  />
                </Field>
              </div>
              <Field label="Description">
                <Input value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
              </Field>
            </>
          ) : (
            <>
              <Field label="Class" required>
                <Select value={form.classroom} onChange={(e) => setForm((f) => ({ ...f, classroom: e.target.value }))}>
                  <option value="">Select a class</option>
                  {classrooms.data.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.academic_year})
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label={modal === 'division' ? 'Division name' : 'Subject name'} required>
                <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
              </Field>
              {modal === 'subject' && (
                <Field label="Subject code">
                  <Input value={form.code} onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))} />
                </Field>
              )}
            </>
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setModal(null)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? <Spinner /> : form.id ? 'Save changes' : 'Create'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}