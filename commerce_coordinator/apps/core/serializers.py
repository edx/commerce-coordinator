"""
Serializers shared between plugins.
"""
from datetime import datetime

from django.utils.translation import gettext_lazy as _
from rest_framework.serializers import *


class UnixDateTimeField(DateTimeField):
    """
    Serializer that accepts a POSIX time value.

    POSIX time is a stricter variant of Unix time which does not count leap seconds.

    Most Unix time values are already in POSIX time.

    This class is a combination of DRF classes IntegerField and DateTimeField.
    """
    default_error_messages = {
        'invalid_int': _('A valid integer is required.'),
        'max_string_length': _('String value too large.'),
        'unparsable_posix_timestamp': _('Could not parse POSIX timestamp.'),
    }

    MAX_STRING_LENGTH = 1000  # Guard against malicious string inputs.

    def to_internal_value(self, value):
        if isinstance(value, str) and len(value) > self.MAX_STRING_LENGTH:
            self.fail('max_string_length')

        try:
            value = int(str(value))
        except (ValueError, TypeError):
            self.fail('invalid_int')

        try:
            value = datetime.fromtimestamp(value)
        except (OverflowError, OSError):
            # Typically restricted to years in 1970 through 2038.
            # Will not catch Unix time stamps that count leap seconds.
            self.fail('unparsable_posix_timestamp')

        # Continue parsing as DateTimeField.
        return super().to_internal_value(value)


# The code in UnixDateTimeField was adapted from encode/django-rest-framework,
# which requires the redistribution of the following BSD 3-Clause License:
#
# Copyright © 2011-present, [Encode OSS Ltd](https://www.encode.io/).
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
