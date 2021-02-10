class TestCloseTooManyArgumentsPlugin:
    def __init__(self):
        self.called = False

    def close(self, cardinal, _):
        """This should never be hit due to wrong number of args."""
        self.called = True


def setup():
    return TestCloseTooManyArgumentsPlugin()
