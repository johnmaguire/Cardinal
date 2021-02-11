from cardinal.decorators import command, help

from googlesearch import search

DEFAULT_MAX_RESULTS = 3


class GoogleSearch:
    def __init__(self, config):
        config = config if config is not None else {}
        self.max_results = config.get('max_results', DEFAULT_MAX_RESULTS)

    @command(['google', 'lmgtfy', 'g'])
    @help("Returns the URL of the top result for a given search query")
    @help("Syntax: .google <query>")
    def query(self, cardinal, user, channel, msg):
        # gets search string from message, and makes it url safe
        try:
            search_string = msg.split(' ', 1)[1]
        except IndexError:
            return cardinal.sendMsg(channel, 'Syntax: .google <query>')

        urls = []
        counter = self.max_results
        for url in search(search_string):
            urls.append(url)

            counter -= 1
            if counter == 0:
                break

        if not urls:
            cardinal.sendMsg(channel, "No results found")
            return
        elif len(urls) == 1:
            cardinal.sendMsg(channel, "Top result for '{}': {}".format(
                search_string,
                urls[0],
            ))
        else:
            cardinal.sendMsg(channel, "Top results for '{}':".format(
                search_string
            ))

            for url in urls:
                cardinal.sendMsg(channel, "  {}".format(url))


entrypoint = GoogleSearch
