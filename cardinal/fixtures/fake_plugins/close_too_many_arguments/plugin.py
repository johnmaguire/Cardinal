from builtins import object
called = False


class TestCloseTooManyArgumentsPlugin(object):
    def close(self, cardinal, _):
        """This should never be hit due to wrong number of args."""
        global called
        called = True


def setup():
    return TestCloseTooManyArgumentsPlugin()
