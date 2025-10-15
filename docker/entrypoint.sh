#!/bin/sh
set -e

# Run migrations
echo "Running Django migrations..."
python manage.py migrate --noinput

# Run main command
exec "$@"
