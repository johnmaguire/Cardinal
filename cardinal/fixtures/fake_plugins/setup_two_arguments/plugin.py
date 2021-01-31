class TestSetupTwoArgumentsPlugin:
    pass


cardinal = None
config = None


def setup(one, two):
    global cardinal, config
    cardinal = one
    config = two

    return TestSetupTwoArgumentsPlugin()
