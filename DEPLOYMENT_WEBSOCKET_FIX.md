# Deployment Configuration Guide

## Current Issue
The deployment is failing because it's trying to use `gunicorn` which doesn't support WebSockets. This Django app uses Django Channels for real-time WebSocket notifications.

## Solution

### Option 1: Use Daphne (Recommended)
Change the deployment start command from:
```bash
gunicorn socipedia.wsgi:application
```

To:
```bash
daphne -b 0.0.0.0 -p $PORT socipedia.asgi:application
```

### Option 2: Use the start.sh script
Use the provided `start.sh` script which:
1. Runs migrations
2. Collects static files
3. Starts the app with daphne

### Why This Matters
- **gunicorn**: Only supports HTTP (WSGI) - WebSocket notifications won't work
- **daphne**: Supports both HTTP and WebSocket (ASGI) - Full functionality

## Deployment Platform Configuration

### For Render.com
1. Go to your service settings
2. Change the "Start Command" from `gunicorn socipedia.wsgi:application` to `daphne -b 0.0.0.0 -p $PORT socipedia.asgi:application`
3. Or use `./start.sh` if you prefer the script approach

### For Heroku
Create a `Procfile` with:
```
web: daphne -b 0.0.0.0 -p $PORT socipedia.asgi:application
```

### For Railway
Use the start command:
```bash
daphne -b 0.0.0.0 -p $PORT socipedia.asgi:application
```

## Environment Variables
Make sure these are set in production:
- `DATABASE_URL`: Your database connection string
- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to `False` in production
- `REDIS_URL`: Redis connection string for channels

## Files Updated
- `requirements.txt`: Added gunicorn for compatibility
- `start.sh`: Created proper startup script
- Fixed WebSocket duplicate notification issue in frontend
