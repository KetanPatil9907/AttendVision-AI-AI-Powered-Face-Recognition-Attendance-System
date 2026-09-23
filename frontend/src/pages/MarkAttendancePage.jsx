import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2, Plus, ScanFace, Trash2, Video, XCircle } from 'lucide-react'
import { api, normalizeError, unwrapList } from '../lib/api.js'
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
import SessionForm from '../components/SessionForm.jsx'

const MAX_PHOTOS = 10
const MAX_SIZE_MB = 10
const confidencePct = (c) => (typeof c === 'number' ? `${(c * 100).toFixed(0)}%` : '—')

const MARK_LABELS = {
  marked: { color: 'green', text: 'Marked present' },
  already_present: { color: 'blue', text: 'Already marked' },
  manual_lock: { color: 'purple', text: 'Manual correction kept' },
  ambiguous: { color: 'amber', text: 'Too close to call' },
  low_quality: { color: 'slate', text: 'Too small / blurry' },
  unknown: { color: 'slate', text: 'Not recognized' },
}

let seq = 0
const nextKey = () => `photo-${Date.now()}-${(seq += 1)}`

/** Collect natural pixel dimensions so bounding boxes can be drawn as % of the image. */
function measure(url) {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => resolve({ w: img.naturalWidth, h: img.naturalHeight })
    img.onerror = () => resolve(null)
    img.src = url
  })
}

export default function MarkAttendancePage() {
  const [sessions, setSessions] = useState([])
  const [sessionId, setSessionId] = useState('')
  const [session, setSession] = useState(null)
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [pageError, setPageError] = useState('')
  const [flash, setFlash] = useState('')

  const [showCreate, setShowCreate] = useState(false)
  const [showCamera, setShowCamera] = useState(false)
  const [items, setItems] = useState([])
  const [processing, setProcessing] = useState(false)
  const [progress, setProgress] = useState(null)
  const [updating, setUpdating] = useState({})
  const [finalizing, setFinalizing] = useState(false)
  const [finalizedCount, setFinalizedCount] = useState(0)

  const loadSessions = useCallback((keepId) => {
    api
      .get('/attendance/sessions/', { params: { status: 'in_progress' } })
      .then((r) => {
        const list = unwrapList(r)
        setSessions(list)
        setSessionId((current) => {
          const stillThere = current && list.some((s) => String(s.id) === String(current))
          const next = stillThere ? current : keepId || (list[0] ? String(list[0].id) : '')
          return next
        })
      })
      .catch((err) => setPageError(normalizeError(err)))
      .finally(() => setLoading(false))
    // Count closed sessions too, so the empty state can explain WHY there is
    // no active session (e.g. "all 3 past sessions are finalized").
    api
      .get('/attendance/sessions/', { params: { status: 'finalized' } })
      .then((r) => {
        const data = r.data
        setFinalizedCount(typeof data?.count === 'number' ? data.count : Array.isArray(data) ? data.length : 0)
      })
      .catch(() => {})
  }, [])

  const loadRecords = useCallback((id) => {
    if (!id) {
      setSession(null)
      setRecords([])
      return
    }
    api
      .get(`/attendance/sessions/${id}/records/`)
      .then((r) => {
        setSession(r.data.session)
        setRecords(Array.isArray(r.data.records) ? r.data.records : [])
      })
      .catch((err) => setPageError(normalizeError(err)))
  }, [])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  useEffect(() => {
    loadRecords(sessionId)
  }, [sessionId, loadRecords])

  const setItemsPatch = (key, patch) =>
    setItems((prev) => prev.map((it) => (it.key === key ? { ...it, ...patch } : it)))

  const addFiles = (files) => {
    const list = Array.isArray(files) ? files : [files]
    setFlash('')

    const rejected = []
    const accepted = []
    for (const file of list) {
      if (!file.type?.startsWith('image/')) rejected.push(`"${file.name}" is not an image`)
      else if (file.size > MAX_SIZE_MB * 1024 * 1024) rejected.push(`"${file.name}" exceeds ${MAX_SIZE_MB} MB`)
      else accepted.push(file)
    }

    const room = MAX_PHOTOS - items.length
    const additions = accepted.slice(0, Math.max(room, 0)).map((file) => {
      const key = nextKey()
      const url = URL.createObjectURL(file)
      measure(url).then((dims) => dims && setItemsPatch(key, { dims }))
      return { key, file, url, dims: null, status: 'queued', error: null, result: null }
    })

    if (rejected.length || accepted.length > additions.length) {
      setPageError(
        [...rejected, ...(accepted.length > additions.length ? [`Only ${MAX_PHOTOS} photos can be added per run`] : [])].join('. '),
      )
    } else if (additions.length) {
      setPageError('')
    }

    if (additions.length) setItems((prev) => [...prev, ...additions])
  }

  const removeItem = (key) => {
    setItems((prev) => {
      const target = prev.find((it) => it.key === key)
      if (target) URL.revokeObjectURL(target.url)
      return prev.filter((it) => it.key !== key)
    })
  }

  const clearItems = () => {
    items.forEach((it) => URL.revokeObjectURL(it.url))
    setItems([])
  }

  const run = async () => {
    if (!session || processing) return
    const pending = items.filter((it) => it.status !== 'done')
    if (!pending.length) return

    setProcessing(true)
    setPageError('')
    setFlash('')
    setProgress({ done: 0, total: pending.length })

    for (let i = 0; i < pending.length; i += 1) {
      const item = pending[i]
      setProgress({ done: i, total: pending.length })
      setItemsPatch(item.key, { status: 'running', error: null })
      try {
        const body = new FormData()
        body.append('image', item.file, item.file.name || 'photo.jpg')
        const res = await api.post(`/attendance/sessions/${session.id}/recognize/`, body)
        setItemsPatch(item.key, { status: 'done', result: res.data })
      } catch (err) {
        setItemsPatch(item.key, { status: 'error', error: normalizeError(err) })
      }
    }

    setProgress({ done: pending.length, total: pending.length })
    setProcessing(false)
    setFlash('Recognition complete — review the roster below.')
    loadRecords(session.id)
    loadSessions(String(session.id))
  }

  const toggleRecord = async (rec) => {
    if (session?.status === 'finalized') return
    const target = rec.status === 'present' ? 'absent' : 'present'
    setUpdating((u) => ({ ...u, [rec.id]: true }))
    setPageError('')
    try {
      await api.post(`/attendance/sessions/${session.id}/update-records/`, {
        updates: [{ id: rec.id, status: target }],
      })
      loadRecords(String(session.id))
    } catch (err) {
      setPageError(normalizeError(err))
    } finally {
      setUpdating({})
    }
  }

  const finalize = async () => {
    if (!session) return
    if (!window.confirm('Finalize this session? Records will be locked and cannot be edited afterwards.'))
      return
    setFinalizing(true)
    setPageError('')
    setFlash('')
    try {
      const res = await api.post(`/attendance/sessions/${session.id}/finalize/`)
      setFlash(res.data.message || 'Session finalized.')
      loadRecords(String(session.id))
      loadSessions()
    } catch (err) {
      setPageError(normalizeError(err))
    } finally {
      setFinalizing(false)
    }
  }

  const onSessionCreated = (created) => {
    setShowCreate(false)
    setFlash('Session created — you can now upload classroom photos.')
    loadSessions(String(created.id))
    setSessionId(String(created.id))
  }

  if (loading) return <PageLoader label="Loading mark attendance…" />

  const isFinalized = session?.status === 'finalized'
  const queued = items.filter((it) => it.status !== 'done')
  const results = items.filter((it) => it.result)
  const totals = results.reduce(
    (acc, it) => ({
      detected: acc.detected + (it.result.detected || 0),
      marked: acc.marked + (it.result.new_marks || 0),
      repeated: acc.repeated + (it.result.repeated || 0),
      unknown: acc.unknown + (it.result.unknown || 0),
      ambiguous: acc.ambiguous + (it.result.ambiguous || 0),
      lowQuality: acc.lowQuality + (it.result.low_quality || 0),
      manual: acc.manual + (it.result.manual_lock || 0),
    }),
    { detected: 0, marked: 0, repeated: 0, unknown: 0, ambiguous: 0, lowQuality: 0, manual: 0 },
  )
  const present = records.filter((r) => r.status === 'present').length
  const total = records.length
  const rate = total ? Math.round((present / total) * 1000) / 10 : 0

  return (
    <div>
      <PageHeader
        title="Mark Attendance"
        subtitle="Upload a classroom photo — the AI recognizes enrolled faces and marks them present"
        actions={
          <Link
            to="/attendance"
            className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <Video className="h-4 w-4" /> All sessions
          </Link>
        }
      />

      {pageError && <div className="mb-4"><Alert>{pageError}</Alert></div>}
      {flash && <div className="mb-4"><Alert variant="success">{flash}</Alert></div>}

      {/* Step 1 - session */}
      <Card className="mb-6 p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-base font-semibold text-slate-800">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">1</span>
            Attendance session
          </h2>
          {session && (
            <div className="flex items-center gap-2">
              <StatusBadge status={session.status} />
              <Link
                to={`/attendance/${session.id}`}
                className="text-sm text-brand-600 hover:underline"
              >
                Open full session →
              </Link>
            </div>
          )}
        </div>

        {!session ? (
          showCreate ? (
            <SessionForm onCreated={onSessionCreated} onCancel={() => setShowCreate(false)} />
          ) : (
            <EmptyState
              title="No active session"
              hint={
                finalizedCount > 0
                  ? `All ${finalizedCount} past session${finalizedCount === 1 ? '' : 's'} ${
                      finalizedCount === 1 ? 'is' : 'are'
                    } finalized — create a new session to keep marking`
                  : 'Create a session for the class, subject and date you want to mark'
              }
              action={
                <Button onClick={() => setShowCreate(true)}>
                  <Plus className="h-4 w-4" /> New session
                </Button>
              }
            />
          )
        ) : (
          <div className="flex flex-wrap items-end gap-4">
            <div className="min-w-56">
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="session-picker">
                Active session
              </label>
              <select
                id="session-picker"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
              >
                {sessions.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.subject_name} · {s.classroom_name} ({s.division_name}) · {s.date}
                  </option>
                ))}
                {!sessions.some((s) => String(s.id) === String(sessionId)) && (
                  <option value={String(session.id)}>
                    {session.subject_name} · {session.date}
                  </option>
                )}
              </select>
            </div>
            <div className="text-sm text-slate-500">
              {session.lecture_number ? `Lecture ${session.lecture_number} · ` : ''}
              {present} / {total || '—'} present
            </div>
            <Button variant="secondary" onClick={() => setShowCreate((v) => !v)}>
              <Plus className="h-4 w-4" /> New session
            </Button>
            {showCreate && (
              <div className="w-full border-t border-slate-100 pt-4">
                <SessionForm onCreated={onSessionCreated} onCancel={() => setShowCreate(false)} />
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Step 2 - photo upload */}
      <Card className="mb-6 p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-base font-semibold text-slate-800">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">2</span>
            Classroom photo{items.length > 1 ? 's' : ''}
          </h2>
          {items.length > 0 && (
            <button onClick={clearItems} className="text-sm text-slate-500 hover:text-slate-700">
              Clear all
            </button>
          )}
        </div>

        {!session ? (
          <div className="py-6 text-center">
            <p className="text-sm text-slate-400">Select or create a session first.</p>
            {!showCreate && (
              <Button className="mt-3" onClick={() => setShowCreate(true)}>
                <Plus className="h-4 w-4" /> New session
              </Button>
            )}
          </div>
        ) : isFinalized ? (
          <Alert variant="warning">
            This session is finalized — records are locked. Create a new session to keep marking.
          </Alert>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <FileUpload
                multiple
                maxFiles={MAX_PHOTOS}
                onSelect={addFiles}
                disabled={processing || items.length >= MAX_PHOTOS}
                hint={`JPG / PNG · up to ${MAX_PHOTOS} photos · max ${MAX_SIZE_MB} MB each`}
                label="Upload classroom photos"
              />
              <div className="space-y-3">
                <div className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
                  <span className="text-slate-600">
                    {showCamera ? 'Capture a frame from the webcam' : 'Prefer live camera?'}
                  </span>
                  <button
                    onClick={() => setShowCamera((v) => !v)}
                    className="font-medium text-brand-600 hover:underline"
                  >
                    {showCamera ? 'Hide camera' : 'Use camera'}
                  </button>
                </div>
                {showCamera && (
                  <CameraCapture
                    compact
                    label="Add captured frame"
                    onCapture={(blob) => {
                      const file = new File([blob], `capture-${Date.now()}.jpg`, { type: 'image/jpeg' })
                      addFiles([file])
                      setShowCamera(false)
                    }}
                  />
                )}
              </div>
            </div>

            {items.length > 0 && (
              <div className="flex flex-wrap gap-3">
                {items.map((it) => (
                  <div
                    key={it.key}
                    className="relative h-24 w-24 overflow-hidden rounded-lg border border-slate-200 bg-slate-100"
                  >
                    <img src={it.url} alt="" className="h-full w-full object-cover" />
                    <span
                      className={[
                        'absolute bottom-0 left-0 right-0 px-1 py-0.5 text-center text-[10px] font-medium text-white',
                        it.status === 'done'
                          ? 'bg-emerald-600/90'
                          : it.status === 'error'
                            ? 'bg-rose-600/90'
                            : it.status === 'running'
                              ? 'bg-brand-600/90'
                              : 'bg-slate-700/80',
                      ].join(' ')}
                    >
                      {it.status === 'done'
                        ? `${it.result?.new_marks || 0} marked`
                        : it.status === 'error'
                          ? 'Failed'
                          : it.status === 'running'
                            ? 'Analyzing…'
                            : 'Queued'}
                    </span>
                    <button
                      onClick={() => removeItem(it.key)}
                      disabled={processing}
                      aria-label="Remove photo"
                      className="absolute right-1 top-1 rounded-md bg-slate-900/60 p-1 text-white hover:bg-slate-900 disabled:opacity-40"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={run} disabled={processing || queued.length === 0}>
                {processing ? <Spinner /> : <ScanFace className="h-4 w-4" />}
                {processing
                  ? `Analyzing ${progress ? progress.done + 1 : 1} of ${progress?.total ?? ''}…`
                  : `Mark attendance${queued.length ? ` (${queued.length} photo${queued.length > 1 ? 's' : ''})` : ''}`}
              </Button>
              <p className="text-xs text-slate-400">
                Only faces matching an enrolled student above the confidence threshold are marked.
              </p>
            </div>
          </div>
        )}
      </Card>

      {/* Step 3 - results */}
      {results.length > 0 && (
        <Card className="mb-6 p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 text-base font-semibold text-slate-800">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">3</span>
              Recognition results
            </h2>
            <div className="flex flex-wrap gap-2 text-xs">
              <Badge color="slate">{totals.detected} face(s)</Badge>
              <Badge color="green">{totals.marked} newly marked</Badge>
              <Badge color="blue">{totals.repeated} already marked</Badge>
              {totals.manual > 0 && <Badge color="purple">{totals.manual} manual hold</Badge>}
              {totals.unknown > 0 && <Badge color="rose">{totals.unknown} unknown</Badge>}
              {totals.ambiguous > 0 && <Badge color="amber">{totals.ambiguous} too close</Badge>}
              {totals.lowQuality > 0 && <Badge color="slate">{totals.lowQuality} low quality</Badge>}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            {results.map((it) => (
              <ResultCard key={it.key} item={it} />
            ))}
          </div>
        </Card>
      )}

      {/* Errors for failed photos */}
      {items.some((it) => it.status === 'error') && (
        <div className="mb-6 space-y-2">
          {items
            .filter((it) => it.status === 'error')
            .map((it) => (
              <Alert key={it.key}>
                <span className="font-medium">{it.file.name}:</span> {it.error}
              </Alert>
            ))}
        </div>
      )}

      {/* Roster */}
      {session && (
        <Card className="mb-6">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
            <h2 className="text-base font-semibold text-slate-800">Session roster</h2>
            <div className="flex items-center gap-2">
              {isFinalized ? (
                <StatusBadge status="finalized" />
              ) : (
                <Button onClick={finalize} disabled={finalizing}>
                  {finalizing ? <Spinner /> : <CheckCircle2 className="h-4 w-4" />} Finalize session
                </Button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 px-5 py-4 sm:grid-cols-4">
            <RosterStat icon={CheckCircle2} tone="emerald" label="Present" value={present} />
            <RosterStat icon={XCircle} tone="rose" label="Absent" value={total - present} />
            <RosterStat icon={ScanFace} tone="brand" label="Total" value={total} />
            <RosterStat icon={Video} tone="amber" label="Rate" value={`${rate}%`} />
          </div>

          {records.length === 0 ? (
            <EmptyState
              title="No students in this session"
              hint="Add students to the division, then create the session again"
            />
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
                      <Td className="font-medium text-slate-900">
                        <span className="flex items-center gap-2">
                          {rec.photo_url ? (
                            <img
                              src={rec.photo_url}
                              alt=""
                              className="h-7 w-7 rounded-full border border-slate-200 object-cover"
                            />
                          ) : (
                            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-500">
                              {rec.student_name?.charAt(0) || '?'}
                            </span>
                          )}
                          {rec.student_name}
                        </span>
                      </Td>
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
        </Card>
      )}
    </div>
  )
}

function RosterStat({ icon: Icon, tone, label, value }) {
  const tones = {
    emerald: 'bg-emerald-100 text-emerald-600',
    rose: 'bg-rose-100 text-rose-600',
    brand: 'bg-brand-100 text-brand-600',
    amber: 'bg-amber-100 text-amber-600',
  }
  return (
    <Card className="flex items-center gap-3 p-4">
      <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${tones[tone]}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-xl font-bold text-slate-900">{value}</p>
        <p className="text-xs text-slate-500">{label}</p>
      </div>
    </Card>
  )
}

function ResultCard({ item }) {
  const { dims, result } = item
  const detections = result?.detections || []
  const pct = (v) => (dims && dims.w ? (v / dims.w) * 100 : 0)
  const pctY = (v) => (dims && dims.h ? (v / dims.h) * 100 : 0)

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200">
      <div className="relative bg-slate-900">
        <img src={item.url} alt="Uploaded classroom" className="block w-full" />
        {dims &&
          detections.map((d, i) => {
            const matched = d.status === 'MATCHED'
            const ambiguous = d.status === 'AMBIGUOUS'
            const lowQ = d.status === 'LOW_QUALITY'
            const color = matched ? '#10b981' : ambiguous ? '#f59e0b' : lowQ ? '#64748b' : '#f43f5e'
            return (
              <div
                key={i}
                className="absolute border-2"
                style={{
                  left: `${pct(d.bbox[0])}%`,
                  top: `${pctY(d.bbox[1])}%`,
                  width: `${pct(d.bbox[2])}%`,
                  height: `${pctY(d.bbox[3])}%`,
                  borderColor: color,
                }}
              >
                <span
                  className="absolute -top-0.5 left-0 max-w-full truncate rounded-br-md px-1 py-0.5 text-[10px] font-semibold leading-tight text-white"
                  style={{ backgroundColor: color }}
                >
                  {matched
                    ? `${d.student_name} ${confidencePct(d.confidence)}`
                    : ambiguous
                      ? `Ambiguous ${confidencePct(d.confidence)}`
                      : lowQ
                        ? 'Too small / blurry'
                        : `Unknown ${confidencePct(d.confidence)}`}
                </span>
              </div>
            )
          })}
        {!dims && (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-slate-400">
            Preparing overlay…
          </div>
        )}
      </div>

      <div className="space-y-2 bg-white p-3">
        <div className="flex flex-wrap gap-1.5 text-[11px]">
          <Badge color="slate">{result?.detected ?? 0} faces</Badge>
          <Badge color="green">{result?.new_marks ?? 0} marked</Badge>
          <Badge color="blue">{result?.repeated ?? 0} already</Badge>
          {(result?.manual_lock || 0) > 0 && <Badge color="purple">{result.manual_lock} manual</Badge>}
          {(result?.unknown || 0) > 0 && <Badge color="rose">{result.unknown} unknown</Badge>}
          {(result?.ambiguous || 0) > 0 && <Badge color="amber">{result.ambiguous} too close</Badge>}
          {(result?.low_quality || 0) > 0 && <Badge color="slate">{result.low_quality} low quality</Badge>}
        </div>
        {detections.length === 0 ? (
          <p className="py-2 text-center text-xs text-slate-400">No faces detected in this photo.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {detections.map((d, i) => {
              const meta = MARK_LABELS[d.mark_status] || MARK_LABELS.unknown
              return (
                <li key={i} className="flex items-center justify-between gap-2 py-1.5 text-xs">
                  <span className="truncate font-medium text-slate-700">
                    {d.student_name ||
                      (d.mark_status === 'ambiguous'
                        ? 'Ambiguous match'
                        : d.mark_status === 'low_quality'
                          ? 'Face quality too low'
                          : 'Unknown')}
                    {d.roll_number ? <span className="ml-1 text-slate-400">#{d.roll_number}</span> : null}
                  </span>
                  <span className="flex shrink-0 items-center gap-1.5">
                    <span className="text-slate-400">{confidencePct(d.confidence)}</span>
                    <Badge color={meta.color}>{meta.text}</Badge>
                  </span>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
