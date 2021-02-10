class TestCloseOneArgumentPlugin:
    def close(self, cardinal):
        self.cardinal = cardinal


def setup():
    return TestCloseOneArgumentPlugin()
