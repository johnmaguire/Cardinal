__author__ = 'tony'

from urllib import urlopen
import json


class UrbanDictPlugin(object):
    def get_ud(self, cardinal, user, channel, msg):
        try:
            word = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, 'Syntax: .ud <word>')
            return

        try:
            url = 'http://api.urbandictionary.com/v0/define?term=' + word
            f = urlopen(url).read()
            data = json.loads(f)

            word_def = data['list'][0]['definition']
            link = data['list'][0]['permalink']

            response = '[ %s ]\n%s\n[ %s ]' % (word, word_def, link)

            cardinal.sendMsg(channel, response.encode('utf-8'))
        except IndexError:
            cardinal.sendMsg(channel, 'Could not retrieve definition for "%s"' % word)

    get_ud.commands = ['ud']
    get_ud.help = ['Returns the top Urban Dictionary definition for a given word.',
                   '.ud <word>']


def setup():
    return UrbanDictPlugin()