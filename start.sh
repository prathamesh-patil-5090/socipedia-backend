#!/usr/bin/env bash

# Run database migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start the application with daphne (supports both HTTP and WebSocket)
exec daphne -b 0.0.0.0 -p $PORT socipedia.asgi:application
