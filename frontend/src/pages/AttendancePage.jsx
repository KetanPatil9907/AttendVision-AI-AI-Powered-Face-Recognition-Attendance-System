import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Plus, Video } from 'lucide-react'
import { api, normalizeError } from '../lib/api.js'
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Modal,
  PageHeader,
  Spinner,
  StatusBadge,
  Td,
  Th,
} from '../components/ui.jsx'
import SessionForm from '../components/SessionForm.jsx'

export default function AttendancePage() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [page, setPage] = useState(1)
  const [count, setCount] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')

  const [modal, setModal] = useState(false)

  const load = (opts = {}) => {
    setLoading(true)
    setError('')
    const params = { page: opts.page ?? page }
    if (opts.status ?? statusFilter) params.status = opts.status ?? statusFilter
    api
      .get('/attendance/sessions/', { params })
      .then((r) => {
        setSessions(r.data.results)
        setCount(r.data.count)
      })
      .catch((err) => setError(normalizeError(err)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, statusFilter])

  const pages = Math.max(1, Math.ceil(count / 20))

  const onCreated = () => {
    setModal(false)
    setStatusFilter('')
    setPage(1)
    load({ page: 1, status: '' })
  }

  return (
    <div>
      <PageHeader
        title="Attendance"
        subtitle="Create and manage attendance sessions"
        actions={
          <Button onClick={() => setModal(true)}>
            <Plus className="h-4 w-4" />
            New session
          </Button>
        }
      />

      {error && <div className="mb-4"><Alert>{error}</Alert></div>}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Button variant={statusFilter === '' ? 'primary' : 'secondary'} onClick={() => { setStatusFilter(''); setPage(1) }}>
          All
        </Button>
        <Button variant={statusFilter === 'in_progress' ? 'primary' : 'secondary'} onClick={() => { setStatusFilter('in_progress'); setPage(1) }}>
          In progress
        </Button>
        <Button variant={statusFilter === 'finalized' ? 'primary' : 'secondary'} onClick={() => { setStatusFilter('finalized'); setPage(1) }}>
          Finalized
        </Button>
      </div>

      <Card>
        {loading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : sessions.length === 0 ? (
          <EmptyState title="No sessions yet" hint="Create a session to start taking attendance" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <Th>Date</Th>
                  <Th>Subject</Th>
                  <Th>Class</Th>
                  <Th>Status</Th>
                  <Th>Present / Total</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sessions.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50">
                    <Td className="font-medium text-slate-900">
                      {s.date}
                      {s.lecture_number && (
                        <span className="ml-2 text-xs font-normal text-slate-400">{s.lecture_number}</span>
                      )}
                    </Td>
                    <Td>{s.subject_name}</Td>
                    <Td>{s.classroom_name} — {s.division_name}</Td>
                    <Td><StatusBadge status={s.status} /></Td>
                    <Td>
                      <Badge color={s.present_count >= s.total_students ? 'green' : 'slate'}>
                        {s.present_count} / {s.total_students || '—'}
                      </Badge>
                    </Td>
                    <Td className="text-right">
                      <Link
                        to={`/attendance/${s.id}`}
                        className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-sm text-brand-600 hover:bg-brand-50"
                      >
                        <Video className="h-4 w-4" /> Open
                      </Link>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {pages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <Button variant="secondary" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
            <ChevronLeft className="h-4 w-4" /> Previous
          </Button>
          <span className="text-sm text-slate-500">Page {page} of {pages}</span>
          <Button variant="secondary" onClick={() => setPage((p) => Math.min(pages, p + 1))} disabled={page >= pages}>
            Next <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      <Modal open={modal} onClose={() => setModal(false)} title="New attendance session" wide>
        <SessionForm onCreated={onCreated} onCancel={() => setModal(false)} />
      </Modal>
    </div>
  )
}