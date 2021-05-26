import logging

from twisted.internet import reactor, defer, protocol
from twisted.web import server, resource


class MySite(server.Site):
    def connectionList(self, *args):
        self.factory.onConnectionLost.callback(self)


class GithubWebhookServer(resource.Resource):
    isLeaf = True

    def __init__(self, recv_hook):
        self.logger = logging.getLogger(__name__)
        self.recv_hook = recv_hook

        super().__init__()

    def render_GET(self, request):
        self.recv_hook('test')

        return ''


class WebPlugin:
    def __init__(self, cardinal):
        self.logger = logging.getLogger(__name__)
        self.serverDisconnected = defer.Deferred()

        self._start_listening(self.serverDisconnected)

    def _start_listening(self, d):
        f = protocol.Factory()
        f.onConnectionLost = d
        f.protocol = MySite

        # It'd be nice if we'd retry if the port was busy...
        self.port = reactor.listenTCP(2273, f)

    def _receive_event(self, event):
        self.logger.debug(f"Received event: {event}")

    @defer.inlineCallbacks
    def close(self, cardinal):
        yield defer.gatherResults([self.port.stopListening(), self.serverDisconnected])


entrypoint = WebPlugin
