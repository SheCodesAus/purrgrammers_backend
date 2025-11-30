release: python manage.py migrate
web: daphne -b 0.0.0.0 -p $PORT backend_save_point.asgi:application