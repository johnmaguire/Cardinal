class TestSetupTwoArgumentsPlugin:
    def __init__(self, cardinal, config):
        self.cardinal = cardinal
        self.config = config


def setup(config, cardinal):
    return TestSetupTwoArgumentsPlugin(cardinal, config)
