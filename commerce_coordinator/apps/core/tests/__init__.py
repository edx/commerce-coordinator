

def name_test(name: str, x):
    """
    Permits the naming of simple ddt packed tests in common collection containers

    This may "feel weird" but it's the way the developers do it see
    `def annotated(str, list)` at https://ddt.readthedocs.io/en/latest/example.html
    """

    class WrappedTuple(tuple):
        pass

    class WrappedList(list):
        pass

    class WrappedDict(dict):
        pass

    wx = None
    if type(x) is dict:
        wx = WrappedDict(x)
    elif type(x) is list:
        wx = WrappedList(x)
    elif type(x) is tuple:
        wx = WrappedTuple(x)

    setattr(wx, "__name__", name)
    return wx
