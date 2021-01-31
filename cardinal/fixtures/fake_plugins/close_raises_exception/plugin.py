class TestCloseRaisesExceptionPlugin:
    def close(self):
        raise Exception()


def setup():
    return TestCloseRaisesExceptionPlugin()
