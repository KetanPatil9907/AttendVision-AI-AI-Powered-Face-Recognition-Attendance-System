import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Users, School, Layers, BookOpen, CalendarCheck, TrendingUp } from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from 'recharts'
import { api, normalizeError } from '../lib/api.js'
import { Alert, Button, Card, PageHeader, PageLoader, StatusBadge } from '../components/ui.jsx'

const barColors = ['#6366f1', '#38bdf8', '#34d399', '#fbbf24', '#f472b6', '#a78bfa']

export default function DashboardPage() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    setError('')
    api
      .get('/dashboard/statistics')
      .then((r) => setData(r.data))
      .catch((err) => setError(normalizeError(err)))
  }, [attempt])

  if (error)
    return (
      <div className="max-w-xl">
        <Alert>{error}</Alert>
        <Button className="mt-3" variant="secondary" onClick={() => setAttempt((a) => a + 1)}>
          Retry
        </Button>
      </div>
    )
  if (!data) return <PageLoader label="Loading dashboard…" />

  const stats = [
    { label: 'Students', value: data.counts.students, icon: Users, color: 'bg-brand-600' },
    { label: 'Classes', value: data.counts.classes, icon: School, color: 'bg-sky-500' },
    { label: 'Divisions', value: data.counts.divisions, icon: Layers, color: 'bg-emerald-500' },
    { label: 'Subjects', value: data.counts.subjects, icon: BookOpen, color: 'bg-amber-500' },
  ]

  return (
    <div>
      <PageHeader
        title={`Welcome back, ${data.teacher.name || data.teacher.title}`}
        subtitle={`Here is what is happening today (${data.today.date})`}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <Card key={label} className="flex items-center gap-4 p-5">
            <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${color} text-white`}>
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{value}</p>
              <p className="text-sm text-slate-500">{label}</p>
            </div>
          </Card>
        ))}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="p-5 lg:col-span-2">
          <div className="mb-4">
            <h3 className="text-base font-semibold text-slate-800">Class-wise attendance</h3>
            <p className="text-xs text-slate-400">Average presence across finalized sessions</p>
          </div>
          {data.class_wise.length === 0 ? (
            <p className="py-10 text-center text-sm text-slate-400">
              Finalize a few attendance sessions to see class-wise trends.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.class_wise}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="classroom" tick={{ fontSize: 12 }} tickLine={false} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                <Tooltip formatter={(v) => [`${v}%`, 'Attendance']} cursor={{ fill: '#f1f5f9' }} />
                <Bar dataKey="percentage" radius={[6, 6, 0, 0]}>
                  {data.class_wise.map((entry, i) => (
                    <Cell key={i} fill={barColors[i % barColors.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card className="p-5">
          <h3 className="mb-3 text-base font-semibold text-slate-800">Today</h3>
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3">
              <span className="flex items-center gap-2 text-slate-500">
                <CalendarCheck className="h-4 w-4" /> Sessions
              </span>
              <span className="font-semibold text-slate-800">{data.today.sessions}</span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3">
              <span className="flex items-center gap-2 text-emerald-600">
                <TrendingUp className="h-4 w-4" /> Present
              </span>
              <span className="font-semibold text-slate-800">
                {data.today.present} / {data.today.present + data.today.absent}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3">
              <span className="text-slate-500">Attendance rate</span>
              <span className="font-semibold text-slate-800">{data.today.percentage}%</span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-brand-50 px-4 py-3">
              <span className="font-medium text-brand-700">Overall average</span>
              <span className="font-semibold text-brand-700">{data.average_attendance}%</span>
            </div>
          </div>
        </Card>
      </div>

      <Card className="mt-6">
        <div className="border-b border-slate-100 px-5 py-4">
          <h3 className="text-base font-semibold text-slate-800">Recent sessions</h3>
        </div>
        {data.recent_sessions.length === 0 ? (
          <p className="py-10 text-center text-sm text-slate-400">
            No sessions yet. <Link to="/attendance" className="text-brand-600 hover:underline">Start one →</Link>
          </p>
        ) : (
          <div className="divide-y divide-slate-100">
            {data.recent_sessions.map((s) => (
              <Link
                key={s.id}
                to={`/attendance/${s.id}`}
                className="flex items-center justify-between px-5 py-3 hover:bg-slate-50"
              >
                <div>
                  <p className="font-medium text-slate-800">
                    {s.subject} — {s.classroom} ({s.division})
                  </p>
                  <p className="text-xs text-slate-400">{s.date}</p>
                </div>
                <StatusBadge status={s.status} />
              </Link>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}