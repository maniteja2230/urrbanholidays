#!/usr/bin/env bash
# build.sh — runs on every deploy on Railway / Render
set -o errexit

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "📁 Collecting static files..."
python manage.py collectstatic --no-input

echo "🗄️  Running database migrations..."
python manage.py migrate --no-input

echo "✅ Build complete!"
