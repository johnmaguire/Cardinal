import logging
import requests
import re
from urllib import quote_plus

from bs4 import BeautifulSoup


class GoogleSearch(object):
    """Original author: Adam 'Flarf' Straub"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def search(self, cardinal, user, channel, msg):
        # gets search string from message, and makes it url safe
        try:
            search_string = msg.split(' ', 1)[1:]
            if len(search_string) < 1:
                return cardinal.sendMsg(channel, 'Syntax: .google <query>')

            search_string = " ".join(search_string)
            search_string = quote_plus(search_string)
        except IndexError:
            return cardinal.sendMsg(channel, 'Syntax: .google <query>')

        try:
            # gets the html of the goole search page, and passes it in to beautiful soup
            google_search = requests.get('https://www.google.com/search?q=%s' % search_string)
            soup = BeautifulSoup(google_search.content, 'html.parser')

            # google search result urls are really weird, this pulls the proper url out of google's <a> tags
            url = re.compile(r'.*(https?:\/\/.+?)\&')
            ols = soup.findAll("ol")

            # iterates through <ol> elements on the page looking for one that looks like
            # <ol>
            #   <li class="g">
            #       <div class="r">
            #            <a> <----- this is the link you're looking for
            #       <div class="s">
            #            # other stuff we don't care about, but this div doesn't exist for add or news elements,
            #              but The div.r exists for those elements.
            for olist in ols:
                # finds all elements the are likely search results
                for result in olist.findAll("li", {"class": "g"}):
                    # finds all elements that contain <div class="s"> and are therfore a search result
                    if result.find("div", {"class": "s"}):
                        href = result.find("a")['href']
                        result = url.match(href).group(1)

                        return cardinal.sendMsg(channel, "Top result is: {0}".format(result))

            return cardinal.sendMsg(channel, "Couldn't find any results for your query :(")
        except:
            self.logger.error("An error occurred searching", exc_info=True)

            return cardinal.sendMsg(channel, "Couldn't find any results for your query :(")

    search.commands = ['google', 'lmgtfy',  'g']
    search.help = ['Returns the URL of the top result for a given search query']

def setup():
    return GoogleSearch()
