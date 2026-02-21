# PricknCare

PAN India Phlebotomist Blood Sample Collection Platform.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11+) |
| Admin Panel | Next.js 14 (App Router) |
| Client Portal | Next.js 14 (App Router) |
| Mobile | Flutter 3.32 (Phlebotomist App) |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |

---

## Prerequisites

- **Python** 3.11+
- **Node.js** 20+
- **pnpm** 10+ — `npm install -g pnpm`
- **Flutter** 3.32 — [flutter.dev/docs/get-started/install](https://flutter.dev/docs/get-started/install)
- **PostgreSQL** 15 (local install)
- **Redis** 7 (local install)
- **pre-commit** — `pip install pre-commit`

---

## Project Structure

```
PricknCare/
├── backend/          # FastAPI backend
├── web/              # Next.js monorepo (Turborepo)
│   ├── apps/
│   │   ├── admin/    # Admin Panel  (port 3000)
│   │   └── client/   # Client Portal (port 3001)
│   └── packages/
│       ├── ui/       # Shared UI components
│       ├── config/   # Shared ESLint, Tailwind, Prettier configs
│       └── types/    # Shared TypeScript types
└── mobile/           # Flutter phlebotomist app
```

---

## Setup

### 1. Clone & environment

```bash
git clone <repo-url>
cd PricknCare
cp .env.example .env
# Edit .env with your local DB credentials
```

### 2. Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
```

### 3. Backend (FastAPI)

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8000
```

### 4. Web (Next.js Monorepo)

```bash
cd web
pnpm install

# Start all apps
pnpm dev

# Or start individually
pnpm dev:admin    # http://localhost:3000
pnpm dev:client   # http://localhost:3001
```

### 5. Mobile (Flutter)

```bash
cd mobile
flutter pub get
flutter run
```

---

## Development Workflow

### Linting

```bash
# Python (from repo root)
black --check backend/
ruff check backend/

# TypeScript/JavaScript (from web/)
cd web && pnpm lint

# Flutter
cd mobile && flutter analyze
```

### Testing

```bash
# Backend
cd backend && pytest

# Web
cd web && pnpm build

# Mobile
cd mobile && flutter test
```

### Pre-commit (runs automatically on `git commit`)

```bash
# Run manually on all files
pre-commit run --all-files

# Skip hooks for a commit (emergency only)
git commit --no-verify -m "..."
```

---

## Database Setup

```sql
-- Create database and user
CREATE USER prickncare WITH PASSWORD 'devpassword';
CREATE DATABASE prickncare OWNER prickncare;
GRANT ALL PRIVILEGES ON DATABASE prickncare TO prickncare;
```

---

## Environment Variables

See [`.env.example`](.env.example) for all required variables.

Key variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `JWT_SECRET_KEY` | JWT signing key (change in production!) |
| `SMS_API_KEY` | MSG91 / Twilio API key |
