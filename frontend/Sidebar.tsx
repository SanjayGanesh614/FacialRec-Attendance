// src/components/shared/Sidebar.tsx
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/utils'
import {
  LayoutDashboard, Users, Building2, CalendarDays,
  BarChart3, Settings, LogOut, Fingerprint, ClipboardList
} from 'lucide-react'

interface NavItem { to: string; icon: React.FC<{ size?: number }>; label: string; adminOnly?: boolean }

const adminNav: NavItem[] = [
  { to: '/admin',             icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/admin/attendance',  icon: ClipboardList,   label: 'Attendance' },
  { to: '/admin/employees',   icon: Users,           label: 'Employees' },
  { to: '/admin/departments', icon: Building2,       label: 'Departments' },
  { to: '/admin/schedule',    icon: CalendarDays,    label: 'Schedule' },
  { to: '/admin/reports',     icon: BarChart3,       label: 'Reports' },
]

const employeeNav: NavItem[] = [
  { to: '/me',          icon: LayoutDashboard, label: 'My Dashboard' },
  { to: '/me/calendar', icon: CalendarDays,    label: 'My Calendar' },
  { to: '/me/history',  icon: ClipboardList,   label: 'History' },
]

export const Sidebar = () => {
  const { user, logout, isAdmin } = useAuthStore()
  const navigate = useNavigate()
  const nav = isAdmin() ? adminNav : employeeNav

  return (
    <aside className="w-[220px] flex-shrink-0 h-screen sticky top-0 flex flex-col border-r border-[var(--border)] bg-[var(--bg-2)]">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-[var(--border)]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[var(--accent)] flex items-center justify-center flex-shrink-0">
            <Fingerprint size={16} className="text-[#0e0e12]" />
          </div>
          <div>
            <p className="font-display font-semibold text-sm leading-none">AttendIQ</p>
            <p className="text-[10px] text-[var(--muted)] font-mono mt-0.5 tracking-wider">ERP SYSTEM</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/admin' || to === '/me'}
            className={({ isActive }) => cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 group',
              isActive
                ? 'bg-[var(--accent-glow)] text-[var(--accent)] font-medium'
                : 'text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--bg-3)]'
            )}
          >
            {({ isActive }) => (
              <>
                <Icon size={15} className={isActive ? 'text-[var(--accent)]' : ''} />
                <span>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User section */}
      <div className="border-t border-[var(--border)] p-3 space-y-1">
        {/* Switch view if admin */}
        {isAdmin() && (
          <button
            onClick={() => navigate('/me')}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--bg-3)] transition-all"
          >
            <Settings size={15} />
            <span>My Profile</span>
          </button>
        )}
        {!isAdmin() && (
          <button
            onClick={() => navigate('/admin')}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--bg-3)] transition-all"
          >
            <LayoutDashboard size={15} />
            <span>Admin View</span>
          </button>
        )}

        {/* User info */}
        <div className="px-3 py-2">
          <p className="text-xs font-medium text-[var(--text)] truncate">{user?.full_name}</p>
          <p className="text-[10px] text-[var(--muted)] font-mono truncate mt-0.5">{user?.role?.replace('_', ' ').toUpperCase()}</p>
        </div>

        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-[var(--muted)] hover:text-[var(--crimson)] hover:bg-[rgba(224,92,107,0.06)] transition-all"
        >
          <LogOut size={15} />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  )
}
