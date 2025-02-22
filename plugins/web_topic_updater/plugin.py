from klein import Klein
from twisted.internet import reactor
from cardinal.decorators import event

class WebTopicUpdater:
    app = Klein()

    def __init__(self, cardinal, config):
        self.cardinal = cardinal
        self.config = config
        self.api_key = config.get('api_key')
        self.port = config.get('port', 8080)
        self.channel = config.get('channel')
        reactor.callInThread(self.run_web_server)

    def run_web_server(self):
        self.app.run('0.0.0.0', self.port)

    @app.route('/update_topic', methods=['GET'])
    def update_topic(self, request):
        api_key = request.args.get(b'api_key', [b''])[0].decode('utf-8')
        new_topic = request.args.get(b'topic', [b''])[0].decode('utf-8')
        channel = request.args.get(b'channel', [self.channel.encode('utf-8')])[0].decode('utf-8')

        if api_key != self.api_key:
            request.setResponseCode(403)
            return b'Forbidden: Invalid API key.'

        if not new_topic:
            request.setResponseCode(400)
            return b'Bad Request: "topic" parameter is required.'

        self.cardinal.sendLine(f"TOPIC {channel} :{new_topic}")
        return b'Topic updated successfully.'
    
entrypoint = WebTopicUpdater

#Usage
#curl "http://127.0.0.1:8080/update_topic?api_key=SecretAPIKey&topic=1New%20Topic%20Here&channel=%23default"