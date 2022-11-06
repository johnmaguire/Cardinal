import re
import logging

from mediawiki import MediaWiki
from mediawiki.exceptions import DisambiguationError
from twisted.internet import defer
from twisted.internet.threads import deferToThread

from cardinal.decorators import command, event, help
from cardinal.exceptions import EventRejectedMessage

ARTICLE_URL_REGEX = r"https?://(?:\w{2}\.)?wikipedia\..{2,4}/wiki/(.+)"

DEFAULT_LANGUAGE_CODE = 'en'
DEFAULT_MAX_DESCRIPTION_LENGTH = 250


# This is used to filter out blank paragraphs
def class_is_not_mw_empty_elt(css_class):
    return css_class != 'mw-empty-elt'


class WikipediaPlugin:
    def __init__(self, cardinal, config):
        """Registers a callback for URL detection."""
        # Initialize logger
        self.logger = logging.getLogger(__name__)

        self._max_description_length = config.get(
            'max_description_length',
            DEFAULT_MAX_DESCRIPTION_LENGTH)

        self._language_code = config.get(
            'language_code',
            DEFAULT_LANGUAGE_CODE)

        self._wiki = None

    @defer.inlineCallbacks
    def get_wiki(self):
        if self._wiki:
            return self._wiki

        # makes a network call
        def get_wiki():
            self._wiki = MediaWiki(
                lang=self._language_code)

        yield deferToThread(get_wiki)

        return self._wiki

    @defer.inlineCallbacks
    def _get_article_info(self, name):
        try:
            w = yield self.get_wiki()
            p = yield deferToThread(w.page, name)
        # FIXME
        except DisambiguationError as err:
            options = "{}".format(', '.join(err.options[:10]))
            if len(err.options) > 10:
                options += ", and {} more".format(len(err.options) - 10)

            return "Wikipedia Disambiguation: {options} - {url}".format(
                options=options,
                url=err.url,
            )

        # makes a network call
        def get_summary(p):
            return "{}...".format(p.summary[:self._max_description_length]) \
                if len(p.summary) > self._max_description_length else \
                p.summary
        summary = yield deferToThread(get_summary, p)

        return "Wikipedia: {title} - {summary} - {url}".format(
            title=p.title,
            summary=summary,
            url=p.url,
        )

    @event('urls.detection')
    @defer.inlineCallbacks
    def url_callback(self, cardinal, channel, url):
        match = re.match(ARTICLE_URL_REGEX, url)
        if not match:
            raise EventRejectedMessage

        try:
            article_info = yield self._get_article_info(match.group(1))
        except Exception:
            self.logger.exception("Error reading Wikipedia API for: {}".format(
                match.group(1)))
            raise EventRejectedMessage

        cardinal.sendMsg(channel, article_info)

    @command(['wiki', 'wikipedia'])
    @help("Gets a summary and link to a Wikipedia page")
    @help("Syntax: @wiki <article>")
    @defer.inlineCallbacks
    def wiki(self, cardinal, user, channel, message):
        name = message.split(' ', 1)[1]

        article_info = yield self._get_article_info(name)
        cardinal.sendMsg(channel, article_info)


entrypoint = WikipediaPlugin
