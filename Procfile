web: gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --max-requests 1000 --preload
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput