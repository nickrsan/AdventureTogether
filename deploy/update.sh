#!/usr/bin/env bash
# ==============================================================================
# AdventureTogether - Remote On-Droplet Application Update & Migration Runner
# ==============================================================================
# This script executes a zero-downtime, state-preserving application update on
# the remote DigitalOcean Droplet. It performs the following sequence:
#
#   1. Syncs the repository with the specified Git branch (default: main)
#   2. Rebuilds updated container images using Docker Compose
#   3. Ensures the PostGIS database container is up and healthy
#   4. Executes Django database migrations in an isolated container
#   5. Collects Django static assets
#   6. Gracefully restarts the application stack without resetting data volumes
#   7. Verifies health of the updated web and API endpoints
#
# Usage:
#   ./update.sh [options]
#   /opt/adventuretogether/deploy/update.sh [options]
#
# Options:
#   --branch, -b <name>   Git branch to pull (default: main)
#   --skip-pull           Skip git pull (use existing workspace files)
#   --skip-migrations     Skip running database migrations
#   --dry-run             Display commands without executing them
#   --help, -h            Show this help message
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# 1. Path & Parameter Resolution
# ------------------------------------------------------------------------------

# Resolve deployment and project directory paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "${SCRIPT_DIR}/docker-compose.yml" ]; then
  DEPLOY_DIR="${SCRIPT_DIR}"
  PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
elif [ -f "${SCRIPT_DIR}/deploy/docker-compose.yml" ]; then
  DEPLOY_DIR="${SCRIPT_DIR}/deploy"
  PROJECT_DIR="${SCRIPT_DIR}"
else
  DEPLOY_DIR="/opt/adventuretogether/deploy"
  PROJECT_DIR="/opt/adventuretogether"
fi

COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"
TARGET_BRANCH="main"
SKIP_PULL="false"
SKIP_MIGRATIONS="false"
DRY_RUN="false"

# Parse CLI options
while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch|-b)
      TARGET_BRANCH="$2"
      shift 2
      ;;
    --skip-pull)
      SKIP_PULL="true"
      shift 1
      ;;
    --skip-migrations)
      SKIP_MIGRATIONS="true"
      shift 1
      ;;
    --dry-run)
      DRY_RUN="true"
      shift 1
      ;;
    --help|-h)
      head -n 25 "$0" | tail -n +3 | sed 's/^# //'
      exit 0
      ;;
    *)
      echo "Error: Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

echo "========================================================================"
echo "    AdventureTogether - Application Update & Zero-Data-Loss Migration   "
echo "========================================================================"
echo "Configuration:"
echo "  Project Directory : ${PROJECT_DIR}"
echo "  Deploy Directory  : ${DEPLOY_DIR}"
echo "  Target Git Branch : ${TARGET_BRANCH}"
echo "  Skip Git Pull     : ${SKIP_PULL}"
echo "  Skip Migrations   : ${SKIP_MIGRATIONS}"
echo "  Dry Run Mode      : ${DRY_RUN}"
echo "========================================================================"

# Helper function to execute or display commands
run_step() {
  local step_description="$1"
  shift
  echo ""
  echo ">>> ${step_description}"
  if [ "${DRY_RUN}" = "true" ]; then
    echo "  [DRY-RUN] Command: $*"
  else
    "$@"
  fi
}

# ------------------------------------------------------------------------------
# 2. Git Codebase Synchronization
# ------------------------------------------------------------------------------

if [ "${SKIP_PULL}" = "false" ]; then
  if [ -d "${PROJECT_DIR}/.git" ]; then
    run_step "Pulling latest changes from branch '${TARGET_BRANCH}'" \
      bash -c "cd '${PROJECT_DIR}' && git fetch origin && git checkout '${TARGET_BRANCH}' && git pull origin '${TARGET_BRANCH}'"
  else
    echo "Notice: '${PROJECT_DIR}' is not a git repository. Skipping git pull."
  fi
else
  echo "Notice: Skipping git pull (--skip-pull specified)."
fi

# ------------------------------------------------------------------------------
# 3. Build Updated Container Images
# ------------------------------------------------------------------------------

run_step "Building updated container images with Docker Compose" \
  docker compose -f "${COMPOSE_FILE}" build --pull

# ------------------------------------------------------------------------------
# 4. Ensure Database Container is Running & Ready
# ------------------------------------------------------------------------------

run_step "Starting PostGIS database container" \
  docker compose -f "${COMPOSE_FILE}" up -d --no-deps db

if [ "${DRY_RUN}" = "false" ]; then
  echo "Waiting for database service readiness..."
  DB_READY=false
  for attempt in {1..30}; do
    if docker compose -f "${COMPOSE_FILE}" exec -T db pg_isready >/dev/null 2>&1; then
      echo "Database is ready (attempt ${attempt}/30)."
      DB_READY=true
      break
    fi
    sleep 2
  done

  if [ "${DB_READY}" = "false" ]; then
    echo "Error: Database did not become ready within 60 seconds." >&2
    exit 1
  fi
fi

# ------------------------------------------------------------------------------
# 5. Execute Django Database Migrations & Collect Static Files
# ------------------------------------------------------------------------------

if [ "${SKIP_MIGRATIONS}" = "false" ]; then
  run_step "Executing Django database migrations in isolated container" \
    docker compose -f "${COMPOSE_FILE}" run --rm backend python manage.py migrate --noinput
else
  echo "Notice: Skipping database migrations (--skip-migrations specified)."
fi

run_step "Collecting Django static files" \
  docker compose -f "${COMPOSE_FILE}" run --rm backend python manage.py collectstatic --noinput

# ------------------------------------------------------------------------------
# 6. Graceful Rolling Restart of Application Stack
# ------------------------------------------------------------------------------

run_step "Restarting application stack containers with updated images" \
  docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans

# ------------------------------------------------------------------------------
# 7. Post-Update Health Verification
# ------------------------------------------------------------------------------

if [ "${DRY_RUN}" = "false" ]; then
  echo ""
  echo ">>> Verifying application health endpoint (http://localhost/api/health/)..."
  HEALTH_SUCCESS=false
  for attempt in {1..20}; do
    if curl -s -f -o /dev/null "http://localhost/api/health/"; then
      echo "Application health check PASSED (attempt ${attempt}/20)."
      HEALTH_SUCCESS=true
      break
    fi
    sleep 2
  done

  if [ "${HEALTH_SUCCESS}" = "false" ]; then
    echo "Warning: Health check did not return HTTP 200 within 40 seconds." >&2
    echo "Check container status and logs with: docker compose -f '${COMPOSE_FILE}' logs" >&2
  fi
fi

echo "========================================================================"
echo "    AdventureTogether Application Update Completed Successfully!        "
echo "========================================================================"
