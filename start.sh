#!/usr/bin/env bash
set -e

echo "Starting container startup script..."

# If GIT_TOKEN is provided, set the origin URL to include it so git lfs can authenticate.
if [ -n "$GIT_TOKEN" ]; then
  echo "Configuring authenticated git remote for LFS..."
  git remote set-url origin "https://${GIT_TOKEN}@github.com/prathamesh-patil-5090/socipedia-backend.git"
fi

git lfs install --local || true

echo "Fetching repository and LFS objects..."
git fetch --all --depth=1 || true

# Attempt to pull LFS objects for combined_model specifically
git lfs pull origin main --include="combined_model/**" || git lfs pull --all || true

# Optional: if combined_model is empty and MODEL_S3_URL is provided, download it
if [ ! -d "combined_model" ] || [ -z "$(ls -A combined_model 2>/dev/null)" ]; then
  if [ -n "$MODEL_S3_URL" ]; then
    echo "Downloading combined_model from MODEL_S3_URL..."
    curl -L "$MODEL_S3_URL" -o /tmp/combined_model.tar.gz
    tar -xzf /tmp/combined_model.tar.gz -C .
    echo "Model downloaded from MODEL_S3_URL."
  else
    echo "combined_model is missing and MODEL_S3_URL not set. Proceeding without model files."
  fi
fi

echo "Running migrations and collectstatic..."
python manage.py migrate --noinput
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
gunicorn socipedia.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-2}
#!/usr/bin/env bash

# Run database migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start the application with daphne (supports both HTTP and WebSocket)
exec daphne -b 0.0.0.0 -p $PORT socipedia.asgi:application
