import { useState } from 'react'
import { NavLink, Outlet, Link, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  School,
  Users,
  ClipboardCheck,
  ScanFace,
  BarChart3,
  FileDown,
  UserCircle,
  Shield,
  LogOut,
  Menu,
  Fingerprint,
} from 'lucide-react'
import { useAuth } from '../lib/auth.jsx'
import { cx } from './ui.jsx'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/classes', label: 'Classes', icon: School },
  { to: '/students', label: 'Students', icon: Users },
  { to: '/attendance', label: 'Sessions', icon: ClipboardCheck },
  { to: '/mark-attendance', label: 'Mark Attendance', icon: ScanFace },
  { to: '/history', label: 'History & Analytics', icon: BarChart3 },
  { to: '/reports', label: 'Reports', icon: FileDown },
]

export default function Layout() {
  const { user, logout, isAdmin } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const items = [...navItems, ...(isAdmin ? [{ to: '/admin', label: 'Administration', icon: Shield }] : [])]

  const sidebar = (
    <div className="flex h-full flex-col bg-slate-900 text-slate-300">
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white">
          <Fingerprint className="h-5 w-5" />
        </div>
        <div>
          <p className="font-semibold text-white">Smart Attendance</p>
          <p className="text-xs text-slate-400">AI Face Recognition</p>
        </div>
      </div>
      <nav className="flex-1 space-y-1 px-3 py-2">
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              cx(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive ? 'bg-brand-600 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white',
              )
            }
          >
            <Icon className="h-4.5 w-4.5" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-slate-800 px-3 py-4">
        <div className="mb-3 flex items-center gap-3 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-700 text-sm font-semibold text-white">
            {user?.name?.charAt(0)?.toUpperCase() || 'T'}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-white">{user?.name || user?.username}</p>
            <p className="text-xs capitalize text-slate-400">
              {user?.role} {user?.title && `· ${user.title}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 px-2">
          <Link
            to="/profile"
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            <UserCircle className="h-4 w-4" />
            Profile
          </Link>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-red-300"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="flex h-full">
      <aside className="hidden w-64 shrink-0 lg:block">{sidebar}</aside>

      <div className={cx('fixed inset-0 z-40 lg:hidden', open ? 'block' : 'hidden')}>
        <div className="absolute inset-0 bg-slate-900/60" onClick={() => setOpen(false)} />
        <div className="absolute inset-y-0 left-0 w-64 shadow-xl">{sidebar}</div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
          <button
            onClick={() => setOpen(true)}
            className="rounded-lg p-2 text-slate-600 hover:bg-slate-100"
            aria-label="Open menu"
            aria-expanded={open}
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="font-semibold text-slate-800">Smart Attendance</span>
          <button
            onClick={handleLogout}
            className="rounded-lg p-2 text-slate-600 hover:bg-slate-100"
            aria-label="Logout"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </header>
        <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}