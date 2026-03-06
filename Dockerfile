FROM python:3.13-alpine

WORKDIR /app

# Copy application files
COPY . .

RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install --no-cache-dir gunicorn

RUN chmod +x /app/run.sh

ENTRYPOINT [ "sh", "-c", "/app/run.sh" ]
