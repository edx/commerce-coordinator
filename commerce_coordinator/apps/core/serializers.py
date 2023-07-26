"""
Serializers shared between plugins.
"""
from datetime import datetime

from django.utils.translation import gettext_lazy as _
from rest_framework.serializers import *  # pylint: disable=wildcard-import; this module extends DRF serializers


class CoordinatorValidationException(Exception):
    """
    An exception to convert verious other caught exceptions to something useful. Currently DRF suppresses
    ValidationErrors. This permits them to be thrown with all their original information intact.
    """

    innerException: Exception = None

    def __init__(self, inner: Exception) -> None:
        """
        Initialize a new CoordinatorValidationException without loosing data from the original Exception

        Args:
            inner: Exception, and Exception we intend to wrap to ensure delivery.
        """
        super().__init__(*inner.args)
        self.innerException = inner


class CoordinatorSerializer(Serializer):
    """
    A custom Coordinator Serializer that eases some basic issues with our hijacking of this mechanism.

    - Suppress lint messages about lack of create() or update().
    - Catch ValidationErrors and pass back CoordinatorValidationException
    """

    # create() and update() are optional. See:
    # https://www.django-rest-framework.org/api-guide/serializers/#saving-instances
    
    type_error = TypeError(
        'CoordinatorSerializer is for model-less validation only.'
    )

    def create(self, validated_data):
        raise self.type_error

    def update(self, instance, validated_data):
        raise self.type_error

    def is_valid(self, *, raise_exception=False):
        try:
            return super().is_valid(raise_exception=raise_exception)
        except ValidationError as inner:
            raise CoordinatorValidationException(inner)


class UnixDateTimeField(DateTimeField):
    """
    Serializer that accepts a POSIX time value.

    POSIX time is a stricter variant of Unix time which does not count leap seconds.

    Most Unix time values are already in POSIX time.

    This class is a combination of DRF classes FloatField and DateTimeField.
    """
    default_error_messages = {
        'invalid_float': _('A valid number is required.'),
        'max_string_length': _('String value too large.'),
        'overflow': _('Integer value too large to convert to float'),
        'unparsable_posix_timestamp': _('Could not parse POSIX timestamp.'),
    }

    MAX_STRING_LENGTH = 1000  # Guard against malicious string inputs.

    def to_internal_value(self, value):
        if isinstance(value, str) and len(value) > self.MAX_STRING_LENGTH:
            self.fail('max_string_length')

        try:
            float_value = float(value)
        except (ValueError, TypeError):
            self.fail('invalid_float')
        except OverflowError:
            self.fail('overflow')

        try:
            datetime_value = datetime.fromtimestamp(float_value)
        except (OverflowError, OSError):
            # Typically restricted to years in 1970 through 2038.
            # Will not catch Unix time stamps that count leap seconds.
            self.fail('unparsable_posix_timestamp')

        # Continue parsing as DateTimeField.
        return super().to_internal_value(datetime_value)

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
