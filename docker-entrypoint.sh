#!/bin/sh
python3 manage.py collectstatic -v 3 --no-input
python3 manage.py migrate -v 3
gunicorn ses_maker.wsgi --log-file - -b :80 --workers=2 --log-level warning
