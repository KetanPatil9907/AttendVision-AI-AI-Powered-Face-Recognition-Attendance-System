import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, FileText, PlayCircle, ScanFace, CheckCircle2, XCircle } from 'lucide-react'
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
  Td,
  Th,
} from '../components/ui.jsx'
import CameraCapture from '../components/CameraCapture.jsx'
import FileUpload from '../components/FileUpload.jsx'

const confidencePct = (c) => (typeof c === 'number' ? `${(c * 100).toFixed(0)}%` : '—')

export default function SessionDetailPage() {
  const { id } = useParams()
  const [session, setSession] = useState(null)
  const [records, setRecords] = useState([])
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [flash, setFlash] = useState('')

  const [recognizing, setRecognizing] = useState(false)
  const [detections, setDetections] = useState([])
  const [lastSummary, setLastSummary] = useState(null)
  const [updating, setUpdating] = useState({})
  const [finalizing, setFinalizing] = useState(false)
  const [showLogs, setShowLogs] = useState(false)

  const loadRecords = useCallback(() => {
    api
      .get(`/attendance/sessions/${id}/records/`)
      .then((r) => {
        setSession(r.data.session)
        setRecords(Array.isArray(r.data.records) ? r.data.records : [])
      })
      .catch((err) => setError(normalizeError(err)))
      .finally(() => setLoading(false))
  }, [id])

  const loadLogs = useCallback(() => {
    api
      .get(`/attendance/sessions/${id}/recognition-logs/`)
      .then((r) => setLogs(r.data.results || r.data.logs || []))
      .catch(() => {})
  }, [id])

  useEffect(() => {
    loadRecords()
  }, [loadRecords])

  const recognizeFrame = async (blob) => {
    setRecognizing(true)
    setError('')
    setFlash('')
    setLastSummary(null)
    try {
      const body = new FormData()
      body.append('image', blob, 'frame.jpg')
      const res = await api.post(`/attendance/sessions/${id}/recognize/`, body)
      setDetections(res.data.detections || [])
      setLastSummary({
        detected: res.data.detected,
        present: res.data.present,
        unknown: res.data.unknown,
        ambiguous: res.data.ambiguous || 0,
        lowQuality: res.data.low_quality || 0,
        newMarks: res.data.new_marks,
        repeated: res.data.repeated,
        manualLock: res.data.manual_lock || 0,
        threshold: res.data.threshold,
      })
      if (res.data.session_status) setSession((s) => ({ ...(s || {}), status: res.data.session_status }))
      loadRecords()
    } catch (err) {
      setError(normalizeError(err))
    } finally {
      setRecognizing(false)
    }
  }

  const toggleRecord = async (rec) => {
    if (session.status === 'finalized') return
    const target = rec.status === 'present' ? 'absent' : 'present'
    setUpdating((u) => ({ ...u, [rec.id]: true }))
    setError('')
    try {
      await api.post(`/attendance/sessions/${id}/update-records/`, {
        updates: [{ id: rec.id, status: target }],
      })
      loadRecords()
    } catch (err) {
      setError(normalizeError(err))
    } finally {
      // Always release the button - the success path used to leave it stuck.
      setUpdating({})
    }
  }

  const finalize = async () => {
    if (!window.confirm('Finalize this session? Records will be locked and cannot be edited afterwards.')) return
    setFinalizing(true)
    setError('')
    setFlash('')
    try {
      const res = await api.post(`/attendance/sessions/${id}/finalize/`)
      if (res.data.session) setSession((s) => ({ ...(s || {}), status: 'finalized' }))
      setFlash(res.data.message || 'Session finalized.')
      loadRecords()
    } catch (err) {
      setError(normalizeError(err))
    } finally {
      setFinalizing(false)
    }
  }

  if (loading) return <PageLoader label="Loading session…" />
  if (error && !session) return <div className="max-w-2xl"><Alert>{error}</Alert></div>
  if (!session) return null

  const isLive = session.status === 'in_progress'
  const isFinalized = session.status === 'finalized'

  return (
    <div>
      <Link to="/attendance" className="mb-4 inline-flex items-center gap-1 text-sm text-brand-600 hover:underline">
        <ArrowLeft className="h-4 w-4" /> Back to attendance sessions
      </Link>

      <PageHeader
        title={`${session.subject_name} — ${session.classroom_name} (${session.division_name})`}
        subtitle={`${session.date}${session.lecture_number ? ` · Lecture ${session.lecture_number}` : ''}`}
        actions={
          isFinalized ? (
            <StatusBadge status="finalized" />
          ) : isLive ? (
            <Button onClick={finalize} disabled={finalizing}>
              {finalizing ? <Spinner /> : <CheckCircle2 className="h-4 w-4" />}
              Finalize session
            </Button>
          ) : (
            <StatusBadge status={session.status} />
          )
        }
      />

      {error && <div className="mb-4"><Alert>{error}</Alert></div>}
      {flash && <div className="mb-4"><Alert variant="success">{flash}</Alert></div>}

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card className="flex items-center gap-3 p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-emerald-600">
            <CheckCircle2 className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xl font-bold text-slate-900">{session.present_count}</p>
            <p className="text-xs text-slate-500">Present</p>
          </div>
        </Card>
        <Card className="flex items-center gap-3 p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-rose-100 text-rose-600">
            <XCircle className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xl font-bold text-slate-900">{session.absent_count}</p>
            <p className="text-xs text-slate-500">Absent</p>
          </div>
        </Card>
        <Card className="flex items-center gap-3 p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-100 text-brand-600">
            <ScanFace className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xl font-bold text-slate-900">{session.total_students}</p>
            <p className="text-xs text-slate-500">Total</p>
          </div>
        </Card>
        <Card className="flex items-center gap-3 p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xl font-bold text-slate-900">{session.percentage}%</p>
            <p className="text-xs text-slate-500">Rate</p>
          </div>
        </Card>
      </div>

      {isLive && (
        <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card className="p-5">
            <h2 className="mb-3 text-base font-semibold text-slate-800">Live recognition</h2>
            <p className="mb-3 text-xs text-slate-400">
              Point the camera at the class and capture — matched students are marked present
              instantly. You can also drag &amp; drop a classroom photo below.
            </p>
            <CameraCapture onCapture={recognizeFrame} capturing={recognizing} />
            <div className="my-4 flex items-center gap-3 text-xs text-slate-400">
              <span className="h-px flex-1 bg-slate-200" />
              or upload a photo
              <span className="h-px flex-1 bg-slate-200" />
            </div>
            <FileUpload
              compact
              onSelect={(file) => recognizeFrame(file)}
              loading={recognizing}
              label="Upload classroom photo"
              hint="Click to upload or drag & drop — the AI marks matched students present"
            />
          </Card>

          <Card className="p-5">
            <h2 className="mb-3 text-base font-semibold text-slate-800">Recognition result</h2>
            {recognizing ? (
              <div className="flex justify-center py-12"><Spinner /></div>
            ) : lastSummary ? (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2 text-xs">
                  <Badge color="slate">{lastSummary.detected} face(s) detected</Badge>
                  <Badge color="green">{lastSummary.present} present</Badge>
                  <Badge color="amber">{lastSummary.newMarks} newly marked</Badge>
                  <Badge color="rose">{lastSummary.repeated} repeated</Badge>
                  {lastSummary.manualLock > 0 && <Badge color="purple">{lastSummary.manualLock} manual hold</Badge>}
                  {lastSummary.unknown > 0 && <Badge color="slate">{lastSummary.unknown} unknown</Badge>}
                  {lastSummary.ambiguous > 0 && <Badge color="amber">{lastSummary.ambiguous} too close</Badge>}
                  {lastSummary.lowQuality > 0 && <Badge color="slate">{lastSummary.lowQuality} low quality</Badge>}
                </div>
                {detections.length === 0 ? (
                  <p className="py-6 text-center text-sm text-slate-400">No detections in this frame.</p>
                ) : (
                  <ul className="space-y-2">
                    {detections.map((d, i) => (
                      <li key={i} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2">
                        <div className="flex items-center gap-3">
                          <span
                            className={`inline-block h-2 w-2 rounded-full ${
                              d.mark_status === 'marked'
                                ? 'bg-emerald-500'
                                : d.mark_status === 'already_present'
                                  ? 'bg-sky-500'
                                  : d.mark_status === 'manual_lock'
                                    ? 'bg-violet-500'
                                    : d.mark_status === 'ambiguous' || d.status === 'AMBIGUOUS'
                                      ? 'bg-amber-500'
                                      : d.mark_status === 'low_quality' || d.status === 'LOW_QUALITY'
                                        ? 'bg-slate-400'
                                        : d.mark_status === 'unknown' || d.status === 'UNKNOWN'
                                          ? 'bg-slate-300'
                                          : 'bg-emerald-500'
                            }`}
                          />
                          <div>
                            <p className="text-sm font-medium text-slate-800">
                              {d.student_name ||
                                (d.mark_status === 'ambiguous'
                                  ? 'Ambiguous match'
                                  : d.mark_status === 'low_quality'
                                    ? 'Face quality too low'
                                    : 'Unknown')}
                              {d.roll_number && <span className="ml-1 text-xs text-slate-400">#{d.roll_number}</span>}
                            </p>
                            <p className="text-xs text-slate-400">
                              {d.mark_status === 'marked'
                                ? 'Attendance marked'
                                : d.mark_status === 'manual_lock'
                                  ? 'Matched — kept as manually marked absent'
                                  : d.status === 'repeated' || d.mark_status === 'already_present'
                                    ? 'Already marked'
                                    : d.mark_status === 'low_quality' || d.status === 'LOW_QUALITY'
                                      ? 'Too small / blurry — not attempted'
                                      : d.mark_status === 'ambiguous' || d.status === 'AMBIGUOUS'
                                        ? 'Too close to call — verify'
                                        : d.status === 'unknown' || d.status === 'UNKNOWN'
                                          ? 'Not recognized'
                                          : d.status}
                              {d.status !== 'LOW_QUALITY' &&
                                typeof d.confidence === 'number' &&
                                ` · ${d.confidence_pct || confidencePct(d.confidence)}`}
                            </p>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : (
              <p className="py-12 text-center text-sm text-slate-400">
                <PlayCircle className="mx-auto mb-2 h-8 w-8 text-slate-300" />
                Capture a frame with the camera to recognize students.
              </p>
            )}
          </Card>
        </div>
      )}

      <Card>
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-base font-semibold text-slate-800">Attendance records</h2>
          <button
            onClick={() => {
              setShowLogs((v) => !v)
              if (!showLogs && logs.length === 0) loadLogs()
            }}
            className="text-sm text-brand-600 hover:underline"
          >
            {showLogs ? 'Hide recognition logs' : 'Show recognition logs'}
          </button>
        </div>

        {records.length === 0 ? (
          <EmptyState title="No records yet" hint="Records are created automatically for each student in the division." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <Th>Student</Th>
                  <Th>Roll</Th>
                  <Th>Status</Th>
                  <Th>Confidence</Th>
                  <Th>Method</Th>
                  <Th className="text-right">Action</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {records.map((rec) => (
                  <tr key={rec.id} className="hover:bg-slate-50">
                    <Td className="font-medium text-slate-900">{rec.student_name}</Td>
                    <Td>{rec.roll_number}</Td>
                    <Td>
                      {rec.status === 'present' ? (
                        <Badge color="green">Present</Badge>
                      ) : (
                        <Badge color="rose">Absent</Badge>
                      )}
                    </Td>
                    <Td>{confidencePct(rec.confidence)}</Td>
                    <Td className="text-xs uppercase text-slate-400">
                      {rec.manually_updated ? 'Manual' : rec.marked_by_ai ? 'AI' : '—'}
                    </Td>
                    <Td className="text-right">
                      {isFinalized ? (
                        <Button variant="ghost" disabled>
                          Locked
                        </Button>
                      ) : (
                        <Button variant="ghost" onClick={() => toggleRecord(rec)} disabled={updating[rec.id]}>
                          {updating[rec.id] ? <Spinner /> : rec.status === 'present' ? 'Mark absent' : 'Mark present'}
                        </Button>
                      )}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {showLogs && (
          <div className="border-t border-slate-100">
            <div className="px-5 py-3 text-sm font-medium text-slate-700">Recognition attempts</div>
            {logs.length === 0 ? (
              <p className="px-5 pb-5 text-sm text-slate-400">No recognition attempts yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50">
                    <tr>
                      <Th>Time</Th>
                      <Th>Student</Th>
                      <Th>Confidence</Th>
                      <Th>Result</Th>
                      <Th>Message</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {logs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-50">
                        <Td>{log.timestamp}</Td>
                        <Td>{log.student_name || log.student || '—'}</Td>
                        <Td>{confidencePct(log.confidence)}</Td>
                        <Td><Badge color={log.result === 'matched' ? 'green' : 'rose'}>{log.result}</Badge></Td>
                        <Td className="text-xs text-slate-500">{log.message || '—'}</Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}