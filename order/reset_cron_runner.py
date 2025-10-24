import os
import django
import time
import schedule

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "framestack.settings")
django.setup()

from django.core.management import call_command

def run_reset_job():
    call_command("reset_expired_plans")

# Run daily at midnight (server time)
schedule.every().day.at("00:00").do(run_reset_job)

while True:
    schedule.run_pending()
    time.sleep(60)
