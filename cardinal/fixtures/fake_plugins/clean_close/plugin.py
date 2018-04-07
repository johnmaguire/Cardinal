class TestCleanClosePlugin(object):
    def close(self):
        pass


def setup():
    return TestCleanClosePlugin()
