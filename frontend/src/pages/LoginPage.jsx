import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { Fingerprint } from 'lucide-react'
import { useAuth } from '../lib/auth.jsx'
import { normalizeError } from '../lib/api.js'
import { Alert, Button, Field, Input, Spinner } from '../components/ui.jsx'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login({ username, password, rememberMe })
      navigate(location.state?.from?.pathname || '/', { replace: true })
    } catch (err) {
      setError(normalizeError(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-lg shadow-brand-600/30">
            <Fingerprint className="h-7 w-7" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Smart Attendance System</h1>
          <p className="mt-1 text-sm text-slate-500">Sign in with your teacher account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          {error && <Alert>{error}</Alert>}
          <Field label="Username or Email" required>
            <Input
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="sir@college.edu"
              autoComplete="username"
            />
          </Field>
          <Field label="Password" required>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </Field>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            />
            Keep me signed in for 30 days
          </label>
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? <Spinner /> : 'Sign in'}
          </Button>
          <Link to="/forgot-password" className="block text-center text-sm text-brand-600 hover:underline">
            Forgot password?
          </Link>
        </form>

        <p className="mt-6 text-center text-xs text-slate-400">
          AI face recognition attendance platform · Backend powered by Django + ONNX Runtime
        </p>
      </div>
    </div>
  )
}