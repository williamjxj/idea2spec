#!/usr/bin/env bash
# reset.sh — Wipe SQLite DB and exported project workspaces, then re-create the DB.
# Use this to start fresh: all saved projects and exported files will be deleted.
#
# Usage:
#   bash scripts/reset.sh          # reset with confirmation prompt
#   bash scripts/reset.sh -f       # force reset, no prompt
#   make reset                     # same as -f

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB_DIR="$ROOT/data"
PROJECTS_DIR="$ROOT/projects"

confirm() {
  if [[ "${1:-}" == "-f" ]]; then
    return 0
  fi
  echo "WARNING: This will DELETE all saved projects and exported workspaces."
  echo "  - Database: $DB_DIR/projects.db"
  echo "  - Exports:  $PROJECTS_DIR/"
  read -r -p "Are you sure? [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]] || exit 1
}

confirm "${1:-}"

# Remove SQLite database
if [ -f "$DB_DIR/projects.db" ]; then
  rm -v "$DB_DIR/projects.db"
  # Also clean up WAL / SHM files if present
  rm -vf "$DB_DIR/projects.db-wal" "$DB_DIR/projects.db-shm"
  echo "→ Database deleted."
else
  echo "→ No database file found at $DB_DIR/projects.db — skipping."
fi

# Remove exported project workspaces
if [ -d "$PROJECTS_DIR" ]; then
  rm -rfv "$PROJECTS_DIR"
  echo "→ Exported workspaces deleted."
else
  echo "→ No projects directory found — skipping."
fi

# Re-create the database by running migrations (requires backend to be running)
echo ""
echo "Done. Restart the backend to auto-create a fresh database:"
echo "  make api"
echo ""
echo "Or if the backend is already running, just hit any endpoint to trigger"
echo "table creation (e.g. curl http://localhost:8100/health)."
