// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'

import { LoginPage } from '@/pages/Login'
import { Layout } from '@/components/shared/Layout'
import { ProtectedRoute } from '@/components/shared/ProtectedRoute'

// Admin pages
import { AdminDashboard }  from '@/pages/admin/Dashboard'
import { AttendancePage }  from '@/pages/admin/Attendance'
import { EmployeesPage }   from '@/pages/admin/Employees'
import { DepartmentsPage } from '@/pages/admin/Departments'
import { ReportsPage }     from '@/pages/admin/Reports'
import { SchedulePage }    from '@/pages/admin/Schedule'

// Employee pages
import { MyDashboard }  from '@/pages/employee/MyDashboard'
import { MyHistory }    from '@/pages/employee/MyHistory'
import { MyCalendar }   from '@/pages/employee/MyCalendar'

const qc = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,       // cache data for 30s before refetching
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Navigate to="/admin" replace />} />

          {/* Admin routes */}
          <Route element={<ProtectedRoute requireAdmin />}>
            <Route element={<Layout />}>
              <Route path="/admin"             element={<AdminDashboard />} />
              <Route path="/admin/attendance"  element={<AttendancePage />} />
              <Route path="/admin/employees"   element={<EmployeesPage />} />
              <Route path="/admin/departments" element={<DepartmentsPage />} />
              <Route path="/admin/schedule"    element={<SchedulePage />} />              <Route path="/admin/reports"     element={<ReportsPage />} />
            </Route>
          </Route>

          {/* Employee routes — all authenticated users can access */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/me"          element={<MyDashboard />} />
              <Route path="/me/calendar" element={<MyCalendar />} />
              <Route path="/me/history"  element={<MyHistory />} />
            </Route>
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </BrowserRouter>

      <Toaster
        position="bottom-right"
        toastOptions={{
          duration: 3500,
          style: {
            background: '#1c1c24',
            color: '#e2e2ea',
            border: '1px solid #2a2a38',
            fontSize: '13px',
            fontFamily: 'DM Sans, sans-serif',
            borderRadius: '8px',
          },
          success: { iconTheme: { primary: '#2dd4a0', secondary: '#1c1c24' } },
          error:   { iconTheme: { primary: '#e05c6b', secondary: '#1c1c24' } },
        }}
      />
    </QueryClientProvider>
  )
}
