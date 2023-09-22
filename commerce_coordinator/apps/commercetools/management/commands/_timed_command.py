from datetime import datetime

from django.core.management import BaseCommand


class TimedCommand(BaseCommand):
    start = datetime.now()

    # Helpers
    def print_reporting_time(self):
        delta = datetime.now() - self.start

        print(f"Started at: {self.start.strftime('%Y-%m-%d, %H:%M:%S')}, took {str(delta)}\n")

    # Django Overrides
    def execute(self, *args, **options):
        ret_val = super().execute(*args, **options)
        self.print_reporting_time()
        return ret_val
