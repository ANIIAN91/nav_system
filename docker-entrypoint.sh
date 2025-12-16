#!/bin/bash
set -e

# Auto-generate SECRET_KEY if not provided
if [ -z "$SECRET_KEY" ]; then
    echo "SECRET_KEY not set, generating random key..."
    export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "Generated SECRET_KEY: ${SECRET_KEY:0:8}..."
fi

# Validate required environment variables
if [ -z "$ADMIN_USERNAME" ]; then
    echo "ERROR: ADMIN_USERNAME environment variable is required"
    exit 1
fi

if [ -z "$ADMIN_PASSWORD" ] && [ -z "$ADMIN_PASSWORD_HASH" ]; then
    echo "ERROR: ADMIN_PASSWORD or ADMIN_PASSWORD_HASH environment variable is required"
    exit 1
fi

# Run database migrations if needed (optional)
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running database migrations..."
    python scripts/migrate_data.py
fi

# Execute the main command
exec "$@"
