from builtins import object
from cardinal.decorators import event


class MultipleEventCallbacksOneFailsPlugin(object):
    @event('foo')
    def A(self, cardinal):
        pass

    @event('foo')
    def z(self, cardinal, wrong_signature):
        pass


def setup():
    return MultipleEventCallbacksOneFailsPlugin()
