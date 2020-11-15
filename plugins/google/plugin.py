from builtins import object
from cardinal.decorators import command, help

from googlesearch import search

MAX_RESULTS = 3


class GoogleSearch(object):
    @command(['google', 'lmgtfy', 'g'])
    @help("Returns the URL of the top result for a given search query")
    @help("Syntax: .google <query>")
    def query(self, cardinal, user, channel, msg):
        # gets search string from message, and makes it url safe
        try:
            search_string = msg.split(' ', 1)[1]
        except IndexError:
            return cardinal.sendMsg(channel, 'Syntax: .google <query>')

        cardinal.sendMsg(channel, "Top results for '%s':" % search_string)

        counter = MAX_RESULTS
        for url in search(search_string):
            cardinal.sendMsg(channel, url)

            counter -= 1
            if counter == 0:
                break


def setup():
    return GoogleSearch()
