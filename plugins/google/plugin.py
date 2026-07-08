import logging

from cardinal.decorators import command, help

from ddgs import DDGS
from twisted.internet import defer
from twisted.internet.threads import deferToThread

DEFAULT_MAX_RESULTS = 3
DEFAULT_BACKEND = 'auto'
MAX_TITLE_LENGTH = 80


def format_result(result):
    # scraped titles can contain junk whitespace or run absurdly long
    title = ' '.join(result['title'].split())
    if len(title) > MAX_TITLE_LENGTH:
        title = title[:MAX_TITLE_LENGTH - 1] + '…'

    return '{} - {}'.format(title, result['href'])


class GoogleSearch:
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)

        config = config if config is not None else {}
        self.max_results = config.get('max_results', DEFAULT_MAX_RESULTS)
        self.backend = config.get('backend', DEFAULT_BACKEND)

    @defer.inlineCallbacks
    @command(['google', 'lmgtfy', 'g'])
    @help("Returns the URL of the top result for a given search query")
    @help("Syntax: .google <query>")
    def query(self, cardinal, user, channel, msg):
        try:
            search_string = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, 'Syntax: .google <query>')
            return

        try:
            results = yield deferToThread(
                DDGS().text,
                search_string,
                backend=self.backend,
                max_results=self.max_results,
            )
        except Exception:
            self.logger.exception("Error searching for: %s", search_string)
            cardinal.sendMsg(channel, "Error fetching search results")
            return

        if not results:
            cardinal.sendMsg(channel, "No results found")
        elif len(results) == 1:
            cardinal.sendMsg(channel, "Top result for '{}': {}".format(
                search_string,
                format_result(results[0]),
            ))
        else:
            cardinal.sendMsg(channel, "Top results for '{}':".format(
                search_string
            ))

            for result in results:
                cardinal.sendMsg(channel, "  {}".format(
                    format_result(result),
                ))


entrypoint = GoogleSearch
