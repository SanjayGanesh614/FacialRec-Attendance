// src/components/shared/Layout.tsx
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

export const Layout = () => (
  <div className="flex min-h-screen">
    <Sidebar />
    <main className="flex-1 min-w-0 overflow-y-auto">
      <div className="p-8 max-w-[1200px] mx-auto page-enter">
        <Outlet />
      </div>
    </main>
  </div>
)
