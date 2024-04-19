import os
import re

import yaml
from django.conf import settings
from django.core.management import BaseCommand

NL = os.linesep

# taken from edx-internal config
START_INDENT = "                "
LIST_INDENT = "    "


class Command(BaseCommand):
    """Django Admin Command to generate YAML config for signals and filters."""

    help = 'Generates YAML config for signals and filters'

    @staticmethod
    def to_yaml(obj) -> str:
        """Convert object to YAML string"""
        return yaml.dump(
            obj,
            default_flow_style=False,
            line_break=NL
        )

    @staticmethod
    def indent_like_edx_internal(string: str) -> str:
        """Indent like edx-internal config YAML format"""
        out = map(
            lambda x: f"{START_INDENT}{x}",
            map(
                lambda x: f"{LIST_INDENT}{x}" if re.search(r"^\s*?- ", x) else x,
                string.split(NL)
            )
        )

        return NL.join(out)

    @staticmethod
    def make_line(line: str, less=0, pad="#") -> str:
        """Pads end of line with # until we hid the width of the terminal"""
        columns, _ = os.get_terminal_size(0)

        return line + pad * ((columns - less) - len(line))

    def handle(self, *args, **options):
        print(f"## {Command.make_line('Coordinator Signals YAML ', less=len(NL)+3)}{NL}")
        print(Command.indent_like_edx_internal(Command.to_yaml(settings.CC_SIGNALS)))
        print(f"{NL}## {Command.make_line('Coordinator Filters YAML ', less=len(NL)*2+3)}{NL}")
        print(Command.indent_like_edx_internal(Command.to_yaml(settings.OPEN_EDX_FILTERS_CONFIG)))
        print(f"{NL}## {Command.make_line('END ', less=len(NL)*2+3)}{NL}")
