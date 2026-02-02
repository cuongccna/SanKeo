#!/bin/bash
# Apply Alembic migrations

set -e

echo "🔄 Running Alembic migrations..."

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Run migrations
alembic upgrade head

echo "✅ Migrations completed successfully!"
