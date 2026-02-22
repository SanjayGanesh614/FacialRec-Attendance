# AttendIQ ERP — React Frontend
## Phase 2: Admin Dashboard + Employee Portal

---

## Setup

```bash
npm install
npm run dev   # → http://localhost:5173
```

The Vite dev server proxies all `/api/*` requests to `http://localhost:8000` (FastAPI backend). Make sure the backend is running first.

---

## Pages Built

### Admin (role: super_admin or manager)
| Route | Page | Description |
|-------|------|-------------|
| `/admin` | Dashboard | Live today's attendance feed, stats |
| `/admin/attendance` | Attendance Records | Filterable table + manual correction |
| `/admin/employees` | Employees | List, create, trigger enrollment |
| `/admin/departments` | Departments | Create/view departments |
| `/admin/reports` | Reports | Monthly breakdown + trend charts |

### Employee (all authenticated users)
| Route | Page | Description |
|-------|------|-------------|
| `/me` | My Dashboard | Personal stats, today's status, gauge |
| `/me/history` | My History | Table + calendar heatmap view |
| `/me/calendar` | My Calendar | Phase 3 placeholder |

---

## Design System

**Aesthetic:** Dark precision-industrial. Bloomberg terminal meets luxury product.

**Fonts:**
- Display headings: Playfair Display (serif)
- Body: DM Sans
- Numbers/code: JetBrains Mono

**Colors:**
- Background: `#0e0e12` / `#14141a` / `#1c1c24`
- Accent (amber gold): `#c9a84c`
- Success (emerald): `#2dd4a0`
- Error (crimson): `#e05c6b`
- Info (sky blue): `#5ba4e8`

---

## Architecture

```
src/
├── api/
│   ├── client.ts       ← Axios instance with auth interceptors + token refresh
│   └── index.ts        ← All API functions
├── store/
│   └── authStore.ts    ← Zustand auth store (persists tokens)
├── types/index.ts      ← TypeScript types matching backend schemas
├── utils/index.ts      ← Formatting helpers
├── components/
│   ├── ui/index.tsx    ← StatCard, Avatar, Modal, Spinner, Pagination...
│   └── shared/
│       ├── Layout.tsx          ← Sidebar + outlet wrapper
│       ├── Sidebar.tsx         ← Navigation (different items per role)
│       └── ProtectedRoute.tsx  ← Route auth guard
└── pages/
    ├── Login.tsx
    ├── admin/
    │   ├── Dashboard.tsx
    │   ├── Attendance.tsx
    │   ├── Employees.tsx
    │   ├── Departments.tsx
    │   └── Reports.tsx
    └── employee/
        ├── MyDashboard.tsx
        └── MyHistory.tsx
```

---

## What's Coming (Phase 3+)

- Schedule intent calendar (employees mark WFH/office/leave)
- Admin mandatory attendance tagging
- No-show alert configuration
- WebSocket live punch feed
- Department-level filtering on all reports
