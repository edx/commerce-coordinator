"""Test core.clients."""

import ddt
from django.test import TestCase

from commerce_coordinator.apps.core.clients import urljoin_directory


@ddt.ddt
class ClientTests(TestCase):
    """Tests of the Client class."""

    @ddt.data(
        ("http://localhost:18130/directory", "/subdirectory"),
        ("http://localhost:18130/directory", "/subdirectory/"),
        ("http://localhost:18130/directory", "subdirectory"),
        ("http://localhost:18130/directory", "subdirectory/"),
        ("http://localhost:18130/directory/", "/subdirectory"),
        ("http://localhost:18130/directory/", "/subdirectory/"),
        ("http://localhost:18130/directory/", "subdirectory"),
        ("http://localhost:18130/directory/", "subdirectory/"),

    )
    @ddt.unpack
    def test_urljoin_directory_trailing_slashes(self, base, suffix):
        output = urljoin_directory(base, suffix)
        expected = "http://localhost:18130/directory/subdirectory"
        self.assertRegex(output, expected + r"/?")
