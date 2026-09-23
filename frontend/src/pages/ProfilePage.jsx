import { useState } from 'react'
import { useAuth } from '../lib/auth.jsx'
import { api, normalizeError } from '../lib/api.js'
import { Alert, Button, Card, Field, Input, PageHeader, Select, Spinner } from '../components/ui.jsx'

const titles = [
  { value: 'sir', label: 'Sir' },
  { value: 'madam', label: 'Madam' },
  { value: 'teacher', label: 'Teacher' },
]

export default function ProfilePage() {
  const { user, refreshUser } = useAuth()
  const [form, setForm] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    email: user?.email || '',
    mobile: user?.mobile || '',
    title: user?.title || 'teacher',
  })
  const [profileMsg, setProfileMsg] = useState('')
  const [profileError, setProfileError] = useState('')
  const [savingProfile, setSavingProfile] = useState(false)

  const [pw, setPw] = useState({ old_password: '', new_password: '', confirm: '' })
  const [pwMsg, setPwMsg] = useState('')
  const [pwError, setPwError] = useState('')
  const [savingPw, setSavingPw] = useState(false)

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const saveProfile = async (e) => {
    e.preventDefault()
    setProfileMsg('')
    setProfileError('')
    setSavingProfile(true)
    try {
      const r = await api.patch('/auth/profile', form)
      setProfileMsg('Profile updated successfully.')
      await refreshUser()
      setForm((f) => ({
        ...f,
        first_name: r.data.first_name || '',
        last_name: r.data.last_name || '',
        email: r.data.email || '',
        mobile: r.data.mobile || '',
        title: r.data.title || 'teacher',
      }))
    } catch (err) {
      setProfileError(normalizeError(err))
    } finally {
      setSavingProfile(false)
    }
  }

  const changePassword = async (e) => {
    e.preventDefault()
    setPwMsg('')
    setPwError('')
    if (pw.new_password !== pw.confirm) {
      setPwError('New passwords do not match.')
      return
    }
    setSavingPw(true)
    try {
      await api.post('/auth/change-password', { old_password: pw.old_password, new_password: pw.new_password })
      setPwMsg('Password changed successfully.')
      setPw({ old_password: '', new_password: '', confirm: '' })
    } catch (err) {
      setPwError(normalizeError(err))
    } finally {
      setSavingPw(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="My Profile" subtitle="Update your account details and password" />

      <div className="space-y-6">
        <Card className="p-6">
          <h2 className="mb-4 text-base font-semibold text-slate-800">Account details</h2>
          <form onSubmit={saveProfile} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {profileError && <div className="sm:col-span-2"><Alert>{profileError}</Alert></div>}
            {profileMsg && <div className="sm:col-span-2"><Alert variant="success">{profileMsg}</Alert></div>}
            <Field label="Username">
              <Input value={user?.username} disabled />
            </Field>
            <Field label="Role">
              <Input value={user?.role} disabled />
            </Field>
            <Field label="First name" required>
              <Input value={form.first_name} onChange={update('first_name')} />
            </Field>
            <Field label="Last name" required>
              <Input value={form.last_name} onChange={update('last_name')} />
            </Field>
            <Field label="Email" required>
              <Input type="email" value={form.email} onChange={update('email')} />
            </Field>
            <Field label="Mobile">
              <Input value={form.mobile} onChange={update('mobile')} />
            </Field>
            <Field label="Title">
              <Select value={form.title} onChange={update('title')}>
                {titles.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </Select>
            </Field>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={savingProfile}>
                {savingProfile ? <Spinner /> : 'Save profile'}
              </Button>
            </div>
          </form>
        </Card>

        <Card className="p-6">
          <h2 className="mb-4 text-base font-semibold text-slate-800">Change password</h2>
          <form onSubmit={changePassword} className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {pwError && <div className="sm:col-span-3"><Alert>{pwError}</Alert></div>}
            {pwMsg && <div className="sm:col-span-3"><Alert variant="success">{pwMsg}</Alert></div>}
            <Field label="Current password" required>
              <Input
                type="password"
                value={pw.old_password}
                onChange={(e) => setPw((p) => ({ ...p, old_password: e.target.value }))}
              />
            </Field>
            <Field label="New password" required hint="At least 8 characters">
              <Input
                type="password"
                value={pw.new_password}
                onChange={(e) => setPw((p) => ({ ...p, new_password: e.target.value }))}
              />
            </Field>
            <Field label="Confirm new password" required>
              <Input
                type="password"
                value={pw.confirm}
                onChange={(e) => setPw((p) => ({ ...p, confirm: e.target.value }))}
              />
            </Field>
            <div className="sm:col-span-3">
              <Button type="submit" disabled={savingPw}>
                {savingPw ? <Spinner /> : 'Change password'}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  )
}