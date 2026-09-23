import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts'
import { api, normalizeError } from '../lib/api.js'
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  PageHeader,
  PageLoader,
  Select,
  Spinner,
  StatusBadge,
  Td,
  Th,
} from '../components/ui.jsx'

const MODES = [
  { key: 'all', label: 'Overall history', endpoint: '/attendance/history' },
  { key: 'trend', label: 'Daily trend', endpoint: '/attendance/trend' },
  { key: 'student', label: 'Student summary', endpoint: null },
]

export default function HistoryPage() {
  const [mode, setMode] = useState('all')
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [studentResults, setStudentResults] = useState([])
  const [chosen, setChosen] = useState(null)
  const [searching, setSearching] = useState(false)
  const searchRef = useRef(null)

  const load = (m, studentId) => {
    setError('')
    setData(null)
    const endpoint =
      m === 'all'
        ? `/attendance/history`
        : m === 'trend'
          ? `/attendance/trend`
          : `/attendance/summary/${studentId}`
    api
      .get(endpoint)
      .then((r) => setData(r.data))
      .catch((err) => setError(normalizeError(err)))
  }

  useEffect(() => {
    setChosen(null)
    setStudentResults([])
    setSearch('')
    if (mode !== 'student') load(mode, null)
  }, [mode])

  const runStudentSearch = async () => {
    if (!search.trim()) return
    setSearching(true)
    try {
      const r = await api.get('/students/', { params: { search: search.trim(), page_size: 10 } })
      setStudentResults(r.data.results)
    } catch (err) {
      setError(normalizeError(err))
    } finally {
      setSearching(false)
    }
  }

  const pickStudent = (s) => {
    setChosen(s)
    setStudentResults([])
    load('student', s.id)
  }

  if (error)
    return (
      <div className="max-w-xl">
        <Alert>{error}</Alert>
        {mode !== 'student' || chosen ? (
          <Button className="mt-3" variant="secondary" onClick={() => load(mode, mode === 'student' ? chosen?.id : null)}>
            Retry
          </Button>
        ) : null}
      </div>
    )

  return (
    <div>
      <PageHeader title="History & Trends" subtitle="Review attendance across sessions, days, or per student" />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {MODES.map((m) => (
          <button
            key={m.key}
            onClick={() => setMode(m.key)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              mode === m.key
                ? 'bg-brand-600 text-white'
                : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {mode === 'student' && (
        <Card className="mb-6 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Input
              ref={searchRef}
              className="max-w-sm"
              placeholder="Search students by name or ID…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setStudentResults([])
              }}
              onKeyDown={(e) => e.key === 'Enter' && runStudentSearch()}
            />
            <Button variant="secondary" onClick={runStudentSearch} disabled={searching}>
              {searching ? <Spinner /> : 'Search'}
            </Button>
          </div>
          {studentResults.length > 0 && (
            <div className="mt-3 overflow-hidden rounded-lg border border-slate-200">
              {studentResults.map((s) => (
                <button
                  key={s.id}
                  onClick={() => pickStudent(s)}
                  className="flex w-full items-center justify-between border-b border-slate-100 px-4 py-2.5 text-left text-sm hover:bg-brand-50"
                >
                  <span className="font-medium text-slate-800">{s.full_name}</span>
                  <span className="text-xs text-slate-400">
                    {s.roll_number} · {s.class_name} — {s.division_name}
                  </span>
                </button>
              ))}
            </div>
          )}
          {chosen && (
            <p className="mt-3 text-xs text-slate-500">
              Summary for <span className="font-semibold">{chosen.full_name}</span>
            </p>
          )}
        </Card>
      )}

      {!data &&
        (mode === 'student' && !chosen ? (
          <Card className="p-10">
            <EmptyState title="Select a student" hint="Search for a student to see their attendance summary" />
          </Card>
        ) : (
          <div className="flex justify-center py-16"><Spinner /></div>
        ))}

      {data && mode !== 'student' && <Overall data={data} mode={mode} />}
      {data && mode === 'student' && <StudentSummary data={data} />}
    </div>
  )
}

function Overall({ data, mode }) {
  if (mode === 'trend') {
    const series = data.series || []
    return (
      <Card className="p-5">
        <h3 className="mb-4 text-base font-semibold text-slate-800">Daily attendance (last 30 days)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={series}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} tickLine={false} interval="preserveStartEnd" />
            <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
            <Tooltip formatter={(v) => [`${v}%`, 'Attendance']} cursor={{ fill: '#f1f5f9' }} />
            <Bar dataKey="percentage" fill="#6366f1" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    )
  }

  const sessions = data.sessions || []
  const totalPresent = sessions.reduce((a, s) => a + s.present, 0)
  const totalAbsent = sessions.reduce((a, s) => a + s.absent, 0)
  const totalAll = totalPresent + totalAbsent

  return (
    <>
      <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Sessions" value={sessions.length} />
        <Metric label="Present" value={totalPresent} accent="text-emerald-600" />
        <Metric label="Absent" value={totalAbsent} accent="text-rose-600" />
        <Metric
          label="Average rate"
          value={totalAll ? `${Math.round((totalPresent / totalAll) * 1000) / 10}%` : '—'}
          accent="text-brand-600"
        />
      </div>

      <Card>
        <div className="border-b border-slate-100 px-5 py-4">
          <h3 className="text-base font-semibold text-slate-800">All sessions</h3>
        </div>
        {sessions.length === 0 ? (
          <EmptyState title="No sessions yet" hint="Create an attendance session to build up history" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <Th>Date</Th>
                  <Th>Subject</Th>
                  <Th>Class</Th>
                  <Th>Present</Th>
                  <Th>Absent</Th>
                  <Th>Rate</Th>
                  <Th>Status</Th>
                  <Th className="text-right">View</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sessions.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50">
                    <Td>{s.date}</Td>
                    <Td>{s.subject}</Td>
                    <Td>{s.classroom} — {s.division}</Td>
                    <Td><Badge color="green">{s.present}</Badge> / {s.total}</Td>
                    <Td><Badge color="rose">{s.absent}</Badge></Td>
                    <Td>{s.percentage}%</Td>
                    <Td><StatusBadge status={s.status} /></Td>
                    <Td className="text-right">
                      <Link to={`/attendance/${s.id}`} className="text-sm text-brand-600 hover:underline">
                        Open
                      </Link>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}

function Metric({ label, value, accent }) {
  return (
    <Card className="p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${accent || 'text-slate-900'}`}>{value}</p>
    </Card>
  )
}

function StudentSummary({ data }) {
  const { student, summary, monthly = [], subjects = [] } = data
  const w = monthly.map((m) => ({ ...m }))
  const s = subjects.map((sub) => ({ ...sub }))
  return (
    <>
      <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Lectures" value={summary.total_lectures} />
        <Metric label="Present" value={summary.present} accent="text-emerald-600" />
        <Metric label="Absent" value={summary.absent} accent="text-rose-600" />
        <Metric label="Attendance" value={`${summary.percentage}%`} accent="text-brand-600" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <h3 className="mb-4 text-base font-semibold text-slate-800">Monthly attendance</h3>
          {w.length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-400">No finalized sessions in this period.</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={w}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} tickLine={false} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                <Tooltip formatter={(v) => [`${v}%`, 'Present']} cursor={{ fill: '#f1f5f9' }} />
                <Bar dataKey="percentage" fill="#38bdf8" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card className="p-5">
          <h3 className="mb-4 text-base font-semibold text-slate-800">Subject-wise attendance</h3>
          {s.length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-400">No subject data available.</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={s}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="subject" tick={{ fontSize: 11 }} tickLine={false} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                <Tooltip formatter={(v) => [`${v}%`, 'Present']} cursor={{ fill: '#f1f5f9' }} />
                <Legend />
                <Bar dataKey="percentage" fill="#34d399" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      <Card className="mt-6">
        <div className="border-b border-slate-100 px-5 py-4">
          <h3 className="text-base font-semibold text-slate-800">Subject breakdown</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr>
                <Th>Subject</Th>
                <Th>Present</Th>
                <Th>Total</Th>
                <Th>Rate</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {s.map((sub) => (
                <tr key={sub.subject_id} className="hover:bg-slate-50">
                  <Td className="font-medium text-slate-900">{sub.subject}</Td>
                  <Td>{sub.present}</Td>
                  <Td>{sub.total}</Td>
                  <Td>{sub.percentage}%</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  )
}