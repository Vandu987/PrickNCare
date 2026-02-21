# Claude Code Instructions — PricknCare Project

## Project Overview
PricknCare is a PAN India Phlebotomist Blood Sample Collection Platform.
- **Backend:** FastAPI (Python)
- **Frontend:** Next.js (Admin Panel + Client Portal)
- **Mobile:** Flutter (Phlebotomist App)
- **Database:** PostgreSQL
- **Cache:** Redis

## Task Master Integration
@./.taskmaster/CLAUDE.md

## ⚠️ STRICT EXECUTION RULES — READ BEFORE DOING ANYTHING

### Rule 1: ALWAYS Follow Task Master
- NEVER write code without a task reference
- ALWAYS check `task-master next` before starting work
- ONLY implement what the current task/subtask says
- DO NOT combine multiple tasks into one implementation

### Rule 2: Execution Flow (MANDATORY for every task)
```
Step 1: task-master show <id>           → Read & understand
Step 2: task-master set-status --id=<id> --status=in-progress  → Mark started
Step 3: Implement ONLY what task says   → Code it
Step 4: Test the implementation         → Verify it works
Step 5: git add . && git commit -m "feat: [task <id>] <desc>"  → Commit
Step 6: task-master set-status --id=<id> --status=done         → Mark done
Step 7: task-master next                → Get next task
```

### Rule 3: Subtask Execution Order
- Tasks have subtasks (e.g., 1.1, 1.2, 1.3)
- Execute subtasks IN ORDER — do 1.1 before 1.2
- Each subtask follows the same 7-step flow above
- When ALL subtasks of a task are done, mark the parent task as done

### Rule 4: Scope Control
- ❌ Do NOT add features not in the task
- ❌ Do NOT refactor unrelated code
- ❌ Do NOT install packages unless task requires it
- ❌ Do NOT modify files outside task scope
- ❌ Do NOT skip tests
- ✅ DO ask for clarification if task is ambiguous
- ✅ DO commit after each subtask completion

### Rule 5: When Stuck
- Use `task-master research "<question>"` for implementation guidance
- Check PRD at `.taskmaster/docs/prd.txt` for business context
- Do NOT guess — ask or research

## Custom Commands Available
- `/execute <id>` — Execute a specific task/subtask with strict workflow
- `/continue` — Resume work from where you left off
- `/status` — Quick project progress dashboard

## Module PRPs (Prompt-Ready Packages)
Reference these for architecture, patterns, and conventions BEFORE implementing any task:

- **Backend:** `.taskmaster/docs/prp/backend-fastapi.md` — FastAPI structure, patterns, dependencies, API standards
- **Frontend:** `.taskmaster/docs/prp/frontend-nextjs.md` — Next.js structure, shadcn/ui, React Query patterns
- **Mobile:** `.taskmaster/docs/prp/mobile-flutter.md` — Flutter structure, Riverpod, offline patterns
- **Database:** `.taskmaster/docs/prp/database-postgresql.md` — Schema, relationships, indexes, status enums
- **Cache:** `.taskmaster/docs/prp/cache-redis.md` — Key patterns, TTLs, caching strategy

### When to Read PRPs:
- Task 1 (Setup) → Read ALL PRPs for full architecture context
- Tasks 2 (DB) → Read `database-postgresql.md` + `cache-redis.md`
- Tasks 3-10 (Backend) → Read `backend-fastapi.md` + `database-postgresql.md` + `cache-redis.md`
- Task 11-12 (Next.js) → Read `frontend-nextjs.md`
- Task 13 (Flutter) → Read `mobile-flutter.md` + reference UI screens from `.taskmaster/docs/ui-screens/`

### UI Screen References (Flutter App — Task 13):
Before building ANY mobile screen, ALWAYS open the matching `screen.png` and `code.html` from `.taskmaster/docs/ui-screens/<folder>/`.
These are the approved designs — match layout, spacing, colors, and components exactly.
See `mobile-flutter.md` for the full screen-to-file mapping table.

## Project Structure
```
PrickNCare/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # API routes
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   ├── services/ # Business logic
│   │   └── core/     # Config, security, deps
│   ├── alembic/      # DB migrations
│   └── tests/
├── web/              # Next.js apps
│   ├── admin/        # Admin Panel
│   ├── client/       # Client Portal
│   └── shared/       # Shared components
├── mobile/           # Flutter app
├── docker-compose.yml
└── .taskmaster/      # Task Master files
```

## Git Commit Convention
- `feat: [task X.X] description` — New feature
- `fix: [task X.X] description` — Bug fix
- `refactor: [task X.X] description` — Code refactor
- `test: [task X.X] description` — Tests
- `chore: [task X.X] description` — Config/setup
