""" Core Module Functions """

import sys


def is_under_test() -> bool:
    """Simply informs us if we are within a testing environment"""
    return (('unittest' in sys.modules or
            'pytest' in sys.modules))
