FROM python:3.5-slim

RUN apt-get update && apt-get install -y \
		gcc \
		gettext \
		postgresql-client libpq-dev \
		sqlite3 \
	--no-install-recommends && rm -rf /var/lib/apt/lists/*

ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN mkdir /code
COPY . /code
WORKDIR /code
RUN manage.py migrate
EXPOSE 8000

CMD gunicorn ses_maker.wsgi --log-file - --workers 2
