from builtins import object
class TestRegistersEventPlugin(object):
    def __init__(self, cardinal):
        cardinal.event_manager.register('test.event', 1)

    def close(self, cardinal):
        cardinal.event_manager.remove('test.event')


def setup(cardinal):
    return TestRegistersEventPlugin(cardinal)
