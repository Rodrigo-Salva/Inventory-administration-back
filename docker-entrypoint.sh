#!/bin/bash
# Docker entrypoint script

set -e

echo "🚀 Starting Inventory SaaS Application..."

# Wait for database to be ready
echo "⏳ Waiting for database..."
until pg_isready -h db -p 5432 -U ${POSTGRES_USER:-postgres}; do
  echo "Database is unavailable - sleeping"
  sleep 2
done

echo "✅ Database is ready!"

# Run migrations
echo "🔄 Running database migrations..."
alembic upgrade head

echo "✅ Migrations complete!"

# Start application
echo "🎉 Starting FastAPI application..."
exec "$@"
