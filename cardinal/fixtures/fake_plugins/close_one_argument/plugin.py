cardinal = None


class TestCloseOneArgumentPlugin:
    def close(self, cardinal_):
        global cardinal
        cardinal = cardinal_


def setup():
    return TestCloseOneArgumentPlugin()
