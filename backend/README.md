# AttendIQ ERP — FastAPI Backend
## Phase 1: Foundation — Auth, Employees, Departments, Attendance, Devices

---

## Setup (do once)

### 1. PostgreSQL
```bash
# macOS
brew install postgresql && brew services start postgresql

# Ubuntu / Raspberry Pi
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql

# Create DB and user
sudo -u postgres psql
  CREATE USER attendiq WITH PASSWORD 'yourpassword';
  CREATE DATABASE attendiq_db OWNER attendiq;
  \q
```

### 2. Python environment
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure
```bash
cp .env.example .env
# Edit .env — fill in DATABASE_URL, JWT_SECRET_KEY, DEVICE_API_KEY at minimum
```

### 4. Run database migrations
```bash
# Option A: Let the app create tables on startup (dev / first run)
# Nothing to do — tables are created automatically in lifespan()

# Option B: Alembic (production — more controlled)
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### 5. Start the server
```bash
# Development (auto-reload)
python app/main.py

# Or with uvicorn directly
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6. Verify
Open http://localhost:8000/docs — you should see the Swagger UI with all endpoints.

---

## API Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/v1/auth/login | None | Get tokens |
| POST | /api/v1/auth/refresh | None | Refresh access token |
| GET | /api/v1/auth/me | Bearer | Own profile |
| GET | /api/v1/employees | Bearer + Admin | List employees |
| POST | /api/v1/employees | Bearer + SuperAdmin | Create employee |
| GET | /api/v1/employees/{id} | Bearer | Get employee |
| PATCH | /api/v1/employees/{id} | Bearer + Admin | Update employee |
| POST | /api/v1/employees/{id}/enroll | Bearer + SuperAdmin | Trigger enrollment |
| GET | /api/v1/departments | Bearer + Admin | List departments |
| POST | /api/v1/departments | Bearer + SuperAdmin | Create department |
| PATCH | /api/v1/departments/{id} | Bearer + SuperAdmin | Update department |
| **POST** | **/api/v1/attendance/punch** | **X-Api-Key** | **Pi sends punch** |
| GET | /api/v1/attendance | Bearer + Admin | Query attendance |
| GET | /api/v1/attendance/today | Bearer + Admin | Today's status |
| GET | /api/v1/attendance/me | Bearer | Own history |
| GET | /api/v1/attendance/summary | Bearer | Monthly stats |
| POST | /api/v1/attendance/correct | Bearer + Admin | Manual correction |
| GET | /api/v1/devices/pending-enrollment | X-Api-Key | Pi polls for work |
| POST | /api/v1/devices/enrollment-complete | X-Api-Key | Pi confirms done |
| POST | /api/v1/devices/unknown-face | X-Api-Key | Report unknown face |

---

## Pi Integration

Update the Pi's `.env`:
```
ERP_BASE_URL=http://YOUR_SERVER_IP:8000
ERP_PUNCH_ENDPOINT=http://YOUR_SERVER_IP:8000/api/v1/attendance/punch
ERP_API_KEY=<same as DEVICE_API_KEY in backend .env>
```

The Pi's `erp_client.py` sends:
```json
{
  "employee_id": "EMP0001",
  "device_id": "pi-door-01",
  "timestamp": "2025-03-15T09:04:22+00:00"
}
```

The backend responds:
```json
{
  "success": true,
  "action": "punch_in",
  "employee_name": "Alice Smith",
  "message": "Punch In — Alice Smith"
}
```

---

## Project Structure

```
app/
├── main.py              ← FastAPI app factory + startup
├── api/v1/
│   ├── router.py        ← Combines all routers
│   └── endpoints/
│       ├── auth.py      ← Login, refresh, me
│       ├── employees.py ← Employee CRUD
│       ├── departments.py
│       ├── attendance.py ← Punch + queries + correction
│       └── devices.py   ← Pi device endpoints
├── core/
│   ├── config.py        ← Settings from .env
│   ├── security.py      ← JWT + bcrypt
│   └── dependencies.py  ← FastAPI Depends()
├── db/
│   ├── base.py          ← Engine + Base
│   └── init_db.py       ← First-run seed
├── models/              ← SQLAlchemy ORM tables
├── schemas/             ← Pydantic request/response
└── services/            ← Business logic
```

---

## What's Next (Phase 2)

- React frontend (admin dashboard + employee portal)
- WebSocket live punch feed
- Monthly attendance charts
- Calendar views
