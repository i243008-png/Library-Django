#!/usr/bin/env bash
# Reset the app to the documented baseline (Linux, macOS, Git Bash, WSL, CI).
# Wipes the database volume, restarts the stack, waits until the app answers,
# then verifies the seeded data. Usage: bash tests/team/baseline/reset.sh [timeout_seconds]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
TIMEOUT="${1:-900}"
COMPOSE=(docker compose -f docker-compose-dev.yml)

echo "1/4 Stopping the stack and deleting its volumes (database, redis, backups)..."
"${COMPOSE[@]}" down -v

echo "2/4 Starting the stack (the seed runs automatically on an empty database)..."
"${COMPOSE[@]}" up -d

echo "3/4 Waiting for http://localhost:8000/api/v1/version/ (up to ${TIMEOUT}s)..."
end=$((SECONDS + TIMEOUT))
until curl -fsS -o /dev/null --max-time 5 http://localhost:8000/api/v1/version/; do
  if [ "$SECONDS" -ge "$end" ]; then
    echo "The app did not become ready. Run: docker compose -f docker-compose-dev.yml logs web" >&2
    exit 1
  fi
  sleep 5
done

echo "4/4 Checking the baseline data..."
"${COMPOSE[@]}" exec -T web python manage.py shell < tests/team/baseline/check_seed.py
echo "Reset complete."
