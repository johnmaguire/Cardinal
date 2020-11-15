from builtins import object
cardinal = None


class TestCloseOneArgumentPlugin(object):
    def close(self, cardinal_):
        global cardinal
        cardinal = cardinal_


def setup():
    return TestCloseOneArgumentPlugin()
