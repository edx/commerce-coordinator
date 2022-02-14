import subprocess

from django.core.management.base import BaseCommand
from django.utils import autoreload


def restart_celery():
    celery_cmd = ('celery', '-A', 'commerce_coordinator', 'worker', '-l', 'INFO')
    kill_cmd = ('pkill', '-f', ' '.join(celery_cmd))
    subprocess.run(kill_cmd)
    subprocess.run(celery_cmd)


class Command(BaseCommand):

    help = 'Starts a commerce-coordiantor celery worker with auto-reload.'

    def handle(self, *args, **options):
        print('Starting celery worker with auto-reload...')
        autoreload.run_with_reloader(restart_celery)
