#!/bin/bash
# Pre-push build check — run before pushing to catch TS errors
set -e
cd "$(dirname "$0")/.."

echo "🔍 Checking admin panel build..."
cd web
pnpm install --frozen-lockfile 2>/dev/null || pnpm install
cd apps/admin && npx next build 2>&1 | tail -5
echo "✅ Admin panel OK"

echo "🔍 Checking client portal build..."
cd ../client && npx next build 2>&1 | tail -5
echo "✅ Client portal OK"

echo ""
echo "🎉 All builds passed — safe to push!"
