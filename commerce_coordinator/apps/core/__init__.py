import sys


def is_under_test() -> bool:
    """Simply informs us if we are within a testing environment"""
    return (('unittest' in sys.modules.keys() or
            'pytest' in sys.modules.keys()))
