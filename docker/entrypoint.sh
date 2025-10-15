#!/bin/sh
set -e

# Run migrations
echo "Running Django migrations..."
python manage.py migrate --noinput

# Start the bot
echo "Starting bot..."
make run-bot
