FROM python:3.11-slim

WORKDIR /updater

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY update-script.py .

RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

COPY updater-cron /etc/cron.d/updater-cron
RUN chmod 0644 /etc/cron.d/updater-cron
RUN crontab /etc/cron.d/updater-cron

RUN mkdir /var/log/cron
CMD ["cron", "-f"]
