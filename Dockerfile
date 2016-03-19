FROM python:3.5-slim

RUN apt-get update && apt-get install -y \
		gcc \
		gettext \
		postgresql-client libpq-dev \
		sqlite3 \
		libxslt-dev \
	--no-install-recommends && rm -rf /var/lib/apt/lists/*

ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN mkdir /code
COPY . /code
WORKDIR /code
EXPOSE 80

ENTRYPOINT ["/code/docker-entrypoint.sh"]
