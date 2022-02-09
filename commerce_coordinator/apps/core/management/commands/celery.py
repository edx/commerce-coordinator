import subprocess

from django.core.management.base import BaseCommand
from django.utils import autoreload


def restart_celery():
    cmd = ('pkill', 'celery')
    subprocess.call(cmd)
    cmd = ('celery', '-A', 'commerce_coordinator', 'worker', '-l', 'INFO')
    subprocess.call(cmd)


class Command(BaseCommand):

    help = 'Starts a commerce-coordiantor celery worker with auto-reload.'

    def handle(self, *args, **options):
        print('Starting celery worker with auto-reload...')
        autoreload.run_with_reloader(restart_celery)
