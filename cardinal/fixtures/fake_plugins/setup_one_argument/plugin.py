class TestSetupOneArgumentPlugin:
    def __init__(self, cardinal):
        self.cardinal = cardinal


def setup(cardinal):
    return TestSetupOneArgumentPlugin(cardinal)
