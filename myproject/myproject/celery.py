import os
import sys

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('myproject')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

if sys.platform == 'win32':
    app.conf.worker_pool = os.getenv('CELERY_WORKER_POOL', 'solo')
