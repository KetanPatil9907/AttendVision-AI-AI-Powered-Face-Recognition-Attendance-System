import { useEffect, useState } from 'react'
import { FileDown } from 'lucide-react'
import { api, normalizeError, unwrapList } from '../lib/api.js'
import {
  Alert,
  Button,
  Card,
  Field,
  Input,
  PageHeader,
  Select,
  Spinner,
} from '../components/ui.jsx'

const reportTypes = [
  { key: 'all', label: 'Complete report' },
  { key: 'daily', label: 'Daily (today)' },
  { key: 'weekly', label: 'Weekly (last 7 days)' },
  { key: 'monthly', label: 'Monthly (this month)' },
  { key: 'class', label: 'Class-wise' },
  { key: 'subject', label: 'Subject-wise' },
  { key: 'student', label: 'Student-wise' },
]

const formats = [
  { key: 'pdf', label: 'PDF' },
  { key: 'xlsx', label: 'Excel (XLSX)' },
  { key: 'csv', label: 'CSV' },
]

const FORMAT_EXT = { pdf: 'application/pdf', xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', csv: 'text/csv' }

export default function ReportsPage() {
  const [classrooms, setClassrooms] = useState([])
  const [subjects, setSubjects] = useState([])
  const [divisions, setDivisions] = useState([])

  const [type, setType] = useState('all')
  const [format, setFormat] = useState('pdf')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [classroom, setClassroom] = useState('')
  const [division, setDivision] = useState('')
  const [subject, setSubject] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    api.get('/classes/classrooms/').then((r) => setClassrooms(unwrapList(r))).catch(() => {})
    api.get('/classes/subjects/').then((r) => setSubjects(unwrapList(r))).catch(() => {})
  }, [])

  useEffect(() => {
    if (!classroom) {
      setDivisions([])
      return
    }
    api
      .get('/classes/divisions/', { params: { classroom } })
      .then((r) => setDivisions(unwrapList(r)))
      .catch(() => {})
  }, [classroom])

  const download = async () => {
    setLoading(true)
    setError('')
    setSuccess('')
    const params = { type, format }
    if (dateFrom) params.date_from = dateFrom
    if (dateTo) params.date_to = dateTo
    if (classroom) params.classroom = classroom
    if (division) params.division = division
    if (subject) params.subject = subject

    try {
      const res = await api.get('/reports/export', { params, responseType: 'blob' })
      const blob = res.data
      const disposition = res.headers['content-disposition'] || ''
      const match = /filename="?([^";]+)"?/.exec(disposition)
      const filename = match?.[1] || `attendance_${type}_report.${format === 'pdf' ? 'pdf' : format === 'xlsx' ? 'xlsx' : 'csv'}`
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      setSuccess(`Report downloaded as ${filename}.`)
    } catch (err) {
      let message = normalizeError(err)
      const data = err?.response?.data
      if (data instanceof Blob && (data.type || '').includes('json')) {
        try {
          const parsed = JSON.parse(await data.text())
          message = parsed.message || message
        } catch {
          /* fall back to generic message */
        }
      }
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <PageHeader title="Reports" subtitle="Download attendance reports in PDF, Excel or CSV" />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="p-6 lg:col-span-2">
          <h2 className="mb-4 text-base font-semibold text-slate-800">Report content</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Report type">
              <Select value={type} onChange={(e) => setType(e.target.value)}>
                {reportTypes.map((t) => (
                  <option key={t.key} value={t.key}>
                    {t.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Output format">
              <Select value={format} onChange={(e) => setFormat(e.target.value)}>
                {formats.map((f) => (
                  <option key={f.key} value={f.key}>
                    {f.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="From date">
              <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            </Field>
            <Field label="To date">
              <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </Field>
            <Field label="Class">
              <Select value={classroom} onChange={(e) => { setClassroom(e.target.value); setDivision('') }}>
                <option value="">All classes</option>
                {classrooms.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.academic_year})
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Division">
              <Select value={division} onChange={(e) => setDivision(e.target.value)} disabled={!classroom}>
                <option value="">{classroom ? 'All divisions' : 'Pick a class first'}</option>
                {divisions.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </Select>
            </Field>
            <div className="sm:col-span-2">
              <Field label="Subject">
                <Select value={subject} onChange={(e) => setSubject(e.target.value)}>
                  <option value="">All subjects</option>
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                      {s.class_name ? ` (${s.class_name})` : ''}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
          </div>

          {error && <div className="mt-4"><Alert>{error}</Alert></div>}
          {success && <div className="mt-4"><Alert variant="success">{success}</Alert></div>}

          <div className="mt-6 flex items-center gap-3">
            <Button onClick={download} disabled={loading}>
              {loading ? <Spinner /> : <FileDown className="h-4 w-4" />}
              Generate {format.toUpperCase()} report
            </Button>
            <p className="text-xs text-slate-400">
              Only finalized sessions are included in reports.
            </p>
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="mb-3 text-base font-semibold text-slate-800">Report types</h2>
          <ul className="space-y-3 text-sm text-slate-500">
            <li><span className="font-medium text-slate-700">Complete:</span> every finalized session with totals.</li>
            <li><span className="font-medium text-slate-700">Daily / Weekly / Monthly:</span> restrict the period; daily uses the most recent session.</li>
            <li><span className="font-medium text-slate-700">Class-wise:</span> aggregated per class + division.</li>
            <li><span className="font-medium text-slate-700">Subject-wise:</span> aggregated per subject.</li>
            <li><span className="font-medium text-slate-700">Student-wise:</span> per-student totals.</li>
          </ul>
        </Card>
      </div>
    </div>
  )
}