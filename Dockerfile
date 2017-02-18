FROM python:3.6-slim

RUN apt-get update && apt-get install -y \
		gcc \
		gettext \
		sqlite3 \
		libmysqlclient18 libmysqlclient-dev \
		libxslt-dev \
	--no-install-recommends && rm -rf /var/lib/apt/lists/*

ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN mkdir /srv/wsgi
COPY . /srv/wsgi
WORKDIR /srv/wsgi
EXPOSE 80

ENTRYPOINT ["/srv/wsgi/docker-entrypoint.sh"]
