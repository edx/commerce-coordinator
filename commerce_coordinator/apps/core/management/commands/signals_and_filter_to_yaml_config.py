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

    # pylint: disable=line-too-long
    def handle(self, *args, **options):
        print(f"## Coordinator Signals YAML ############################################################################{NL}")
        print(Command.indent_like_edx_internal(Command.to_yaml(settings.CC_SIGNALS)))
        print(f"{NL}{NL}## Coordinator Filters YAML ####################################################################{NL}")
        print(Command.indent_like_edx_internal(Command.to_yaml(settings.OPEN_EDX_FILTERS_CONFIG)))
        print(f"{NL}{NL}## END  ########################################################################################{NL}")

    # pylint: enable=line-too-long
