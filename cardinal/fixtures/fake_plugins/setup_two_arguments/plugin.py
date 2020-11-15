from builtins import object
class TestSetupTwoArgumentsPlugin(object):
    pass


cardinal = None
config = None


def setup(one, two):
    global cardinal, config
    cardinal = one
    config = two

    return TestSetupTwoArgumentsPlugin()
