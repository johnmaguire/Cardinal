import logging

import requests
from twisted.internet import defer
from twisted.internet.threads import deferToThread

from cardinal.decorators import command, help


API_URL = "https://api.wolframalpha.com/v1/result?appid={app_id}&i={query}"


class WolframAlphaPlugin:
    def __init__(self, config):
        self.app_id = config.get('app_id', None)
        if not self.app_id:
            raise Exception("Please set app_id in plugin config")
        self.logger = logging.getLogger(__name__)

    @defer.inlineCallbacks
    def make_query(self, query):
        self.logger.debug("Making query to Wolfram Alpha: %s", query)

        r = yield deferToThread(requests.get, API_URL.format(
            app_id=self.app_id,
            query=query,
        ))
        r.raise_for_status()
        answer = r.text

        self.logger.debug("Got answer for query '%s': %s", query, answer)

        return answer

    @command(['wolfram', 'calc'])
    @help('Make a query with Wolfram Alpha')
    @help('Syntax: .wolfram <query>')
    @defer.inlineCallbacks
    def wolfram(self, cardinal, user, channel, message):
        try:
            query = message.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .wolfram <query>")
            return

        try:
            answer = yield self.make_query(query)
        except Exception:
            cardinal.sendMsg(channel, "Couldn't parse the query or result")
            return

        cardinal.sendMsg(channel, "{}: {}".format(user.nick, answer))


def setup(_, config):
    return WolframAlphaPlugin(config)
