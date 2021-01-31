class TestSetupOneArgumentPlugin:
    pass


cardinal = None


def setup(one):
    global cardinal
    cardinal = one

    return TestSetupOneArgumentPlugin()
