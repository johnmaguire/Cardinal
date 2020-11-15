from builtins import object
class TestCloseNoArgumentsPlugin(object):
    def close(self):
        pass


def setup():
    return TestCloseNoArgumentsPlugin()
