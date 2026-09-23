import { useEffect, useState } from 'react'
import { ShieldCheck, UserPlus } from 'lucide-react'
import { api, normalizeError, unwrapList } from '../lib/api.js'
import {
  Alert,
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

const titles = ['sir', 'madam', 'teacher']

export default function AdminPage() {
  const [teachers, setTeachers] = useState([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    title: 'teacher',
    mobile: '',
  })

  const load = () => {
    setLoading(true)
    setError('')
    api
      .get('/auth/teachers')
      .then((r) => setTeachers(unwrapList(r)))
      .catch((err) => setError(normalizeError(err)))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const createTeacher = async (e) => {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      await api.post('/auth/register-teacher', form)
      setOpen(false)
      setForm({ username: '', email: '', password: '', first_name: '', last_name: '', title: 'teacher', mobile: '' })
      load()
    } catch (err) {
      setError(normalizeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Administration"
        subtitle="Create and manage teacher accounts"
        actions={
          <Button onClick={() => setOpen(true)}>
            <UserPlus className="h-4 w-4" />
            New teacher
          </Button>
        }
      />

      <Card>
        {loading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : teachers.length === 0 ? (
          <EmptyState title="No teachers registered" hint="Use “New teacher” to add your first account" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <Th>Name</Th>
                  <Th>Username</Th>
                  <Th>Email</Th>
                  <Th>Title</Th>
                  <Th>Mobile</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {teachers.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-50">
                    <Td className="font-medium text-slate-900">{t.name}</Td>
                    <Td>{t.username}</Td>
                    <Td>{t.email || '—'}</Td>
                    <Td className="capitalize">{t.title || '—'}</Td>
                    <Td>{t.mobile || '—'}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="Create teacher account">
        <form onSubmit={createTeacher} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2 flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
            <ShieldCheck className="h-4 w-4" />
            Only administrators can create teacher accounts.
          </div>
          {error && <div className="sm:col-span-2"><Alert>{error}</Alert></div>}
          <Field label="Username" required>
            <Input value={form.username} onChange={update('username')} />
          </Field>
          <Field label="Email" required>
            <Input type="email" value={form.email} onChange={update('email')} />
          </Field>
          <Field label="First name" required>
            <Input value={form.first_name} onChange={update('first_name')} />
          </Field>
          <Field label="Last name" required>
            <Input value={form.last_name} onChange={update('last_name')} />
          </Field>
          <Field label="Password" required hint="At least 8 characters">
            <Input type="password" value={form.password} onChange={update('password')} />
          </Field>
          <Field label="Title">
            <Select value={form.title} onChange={update('title')}>
              {titles.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </Select>
          </Field>
          <Field label="Mobile">
            <Input value={form.mobile} onChange={update('mobile')} />
          </Field>
          <div className="sm:col-span-2 flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? <Spinner /> : 'Create account'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}