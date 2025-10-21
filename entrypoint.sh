#!/bin/sh

# Apply database migrations
echo "Applying database migrations..."
uv run src/manage.py migrate --noinput

# Start the main process
exec "$@"
