#!/bin/sh
set -e

echo "→ Aplicando migraciones..."
python manage.py migrate --noinput

echo "→ Recolectando estáticos..."
python manage.py collectstatic --noinput

echo "→ Iniciando Gunicorn..."
exec gunicorn urlmonitor.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
