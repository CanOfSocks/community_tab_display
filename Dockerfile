FROM 3.13-alpine

WORKDIR /app

# Copy application files
COPY . .

RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install --no-cache-dir gunicorn

ENTRYPOINT [ "sh", "-c", "/app/startCron.sh" ]
