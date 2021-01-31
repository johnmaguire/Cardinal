from cardinal.decorators import event


class MultipleEventCallbacksOneFailsPlugin:
    @event('foo')
    def A(self, cardinal):
        pass

    @event('foo')
    def z(self, cardinal, wrong_signature):
        pass


def setup():
    return MultipleEventCallbacksOneFailsPlugin()
