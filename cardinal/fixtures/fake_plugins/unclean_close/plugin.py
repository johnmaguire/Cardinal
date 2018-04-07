class TestUncleanClosePlugin(object):
    def close(self):
        raise Exception()


def setup():
    return TestUncleanClosePlugin()
