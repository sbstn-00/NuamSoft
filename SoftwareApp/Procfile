release: python manage.py migrate && python manage.py collectstatic --noinput && python manage.py createsuperuser --noinput
web: gunicorn SoftwareApp.wsgi