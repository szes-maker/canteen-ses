#!/bin/sh
python3 manage.py collectstatic -v 3 --no-input
python3 manage.py migrate -v 3
python3 manage.py clearsessions
gunicorn ses_maker.wsgi --log-file - -b :$PORT --workers=3 --max-requests=800 --max-requests-jitter=400 --log-level info
