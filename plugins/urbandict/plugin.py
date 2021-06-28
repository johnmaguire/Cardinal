import logging

from cardinal.decorators import command, help

import requests
from twisted.internet import defer
from twisted.internet.threads import deferToThread

URBANDICT_API_PREFIX = 'http://api.urbandictionary.com/v0/define'


class UrbanDictPlugin:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @defer.inlineCallbacks
    @command(['ud', 'urbandict'])
    @help('Returns the top Urban Dictionary definition for a given word.')
    @help('Syntax: @ud <word>')
    def get_ud(self, cardinal, user, channel, msg):
        try:
            word = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, 'Syntax: .ud <word>')
            return

        try:
            url = URBANDICT_API_PREFIX
            r = yield deferToThread(requests.get, url, params={'term': word})

            data = r.json()
            entry = data['list'].pop(0)

            definition = entry['definition']
            thumbs_up = entry['thumbs_up']
            thumbs_down = entry['thumbs_down']
            link = entry['permalink']

            response = 'UD [%s]: %s [\u25b2%d|\u25bc%d] - %s' % (
                word, definition, thumbs_up, thumbs_down, link
            )

            cardinal.sendMsg(channel, response)
        except Exception:
            self.logger.exception("Error with definition: %s", word)
            cardinal.sendMsg(channel,
                             "Could not retrieve definition for %s" % word)


entrypoint = UrbanDictPlugin
