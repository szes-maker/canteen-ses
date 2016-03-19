#!/bin/sh
python3 manage.py collectstatic -v 3 --no-input
python3 manage.py migrate
gunicorn ses_maker.wsgi --log-file - -b 0.0.0.0:80 --workers=2
