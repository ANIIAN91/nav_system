#!/bin/bash
set -e

# Validate required environment variables
if [ -z "$SECRET_KEY" ]; then
    echo "ERROR: SECRET_KEY environment variable is required"
    exit 1
fi

if [ -z "$ADMIN_USERNAME" ]; then
    echo "ERROR: ADMIN_USERNAME environment variable is required"
    exit 1
fi

if [ -z "$ADMIN_PASSWORD" ] && [ -z "$ADMIN_PASSWORD_HASH" ]; then
    echo "ERROR: ADMIN_PASSWORD or ADMIN_PASSWORD_HASH environment variable is required"
    exit 1
fi

# Run database migrations by default.
if [ "$SKIP_MIGRATIONS" = "true" ]; then
    echo "SKIP_MIGRATIONS=true, skipping database migrations."
else
    if [ ! -f "/app/alembic.ini" ] || [ ! -d "/app/alembic/versions" ] || [ "$(ls -1 /app/alembic/versions/*.py 2>/dev/null | wc -l)" -eq 0 ]; then
        echo "ERROR: Alembic configuration or revisions are missing. Refusing to start without migrations."
        echo "Set SKIP_MIGRATIONS=true only if migrations are executed externally."
        exit 1
    fi

    echo "Running database migrations (alembic upgrade head)..."
    alembic upgrade head
fi

# Execute the main command
exec "$@"
