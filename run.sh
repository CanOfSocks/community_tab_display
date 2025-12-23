#!/bin/sh
set -e

exec gunicorn \
  -w ${GUNICORN_WORKERS:-4} \
  -b ${GUNICORN_BIND:-0.0.0.0:9000} \
  --keep-alive ${GUNICORN_KEEP_ALIVE:-5} \
  --max-requests ${GUNICORN_MAX_REQUESTS:-1000} \
  --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER:-100} \
  --chdir /app/ \
  app:app

