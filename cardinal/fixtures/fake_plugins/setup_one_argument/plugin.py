from builtins import object
class TestSetupOneArgumentPlugin(object):
    pass


cardinal = None


def setup(one):
    global cardinal
    cardinal = one

    return TestSetupOneArgumentPlugin()
