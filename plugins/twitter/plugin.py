import re
from urllib.parse import urlparse

import requests
import twitter
from twisted.internet import defer
from twisted.internet.threads import deferToThread

from cardinal.decorators import event
from cardinal.exceptions import EventRejectedMessage


class TwitterPlugin:
    def __init__(self, config):
        consumer_key = config['consumer_key']
        consumer_secret = config['consumer_secret']

        if not all([consumer_key, consumer_secret]):
            raise Exception(
                "Twitter plugin requires consumer_key and consumer_secret"
            )

        self.api = twitter.Api(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            application_only_auth=True,
        )

    @defer.inlineCallbacks
    def get_tweet(self, tweet_id):
        tweet = yield deferToThread(self.api.GetStatus,
                                    tweet_id)

        return tweet

    @defer.inlineCallbacks
    def follow_short_link(self, url):
        r = yield deferToThread(requests.get,
                                url)

        # Twitter returns 400 in normal operation
        if not r.ok and r.status_code != 400:
            r.raise_for_status()

        return r.url

    @event('urls.detection')
    @defer.inlineCallbacks
    def handle_tweet(self, cardinal, channel, url):
        o = urlparse(url)

        # handle t.co short links
        if o.netloc == 't.co':
            url = yield self.follow_short_link(url)
            o = urlparse(url)

        if o.netloc == 'twitter.com' \
                and (match := re.match(r'^/.*/status/(\d+)$', o.path)):
            tweet_id = match.group(1)

            t = yield self.get_tweet(tweet_id)
            cardinal.sendMsg(channel, "Tweet from @{}: {}".format(
                t.user.screen_name,
                t.text,
            ))
        else:
            raise EventRejectedMessage


entrypoint = TwitterPlugin
