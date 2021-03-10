import logging
import re
from urllib.parse import urlparse

import requests
from twisted.internet import defer
from twisted.internet.threads import deferToThread

from cardinal.decorators import event
from cardinal.exceptions import EventRejectedMessage


class ImgurPlugin:
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.api = ImgurApi(config['client_id'])

    @event("urls.detection")
    @defer.inlineCallbacks
    def handle_url(self, cardinal, channel, url):
        o = urlparse(url)
        if o.netloc not in ('i.imgur.com', 'imgur.com'):
            raise EventRejectedMessage

        # it's not really possible to tell if this is an image or an album
        if match := re.match(r'^(?:.*?)/(\w+)(?:\.\w+)?$', o.path):
            imgur_hash = match.group(1)
            try:
                image = yield self.api.get_image(imgur_hash)
                cardinal.sendMsg(channel, self.format_image(image))
                return
            except requests.exceptions.HTTPError:
                # probably not an image. no support for other types currently
                raise EventRejectedMessage

        raise EventRejectedMessage

    def format_image(self, image):
        # [imgur] 86533 views  image/jpeg 1900x1200 [nsfw]
        return f"[imgur] {image['views']:,} views  " \
            f"{image['type']} {image['width']}x{image['height']}" + (
                " [nsfw]" if image['nsfw'] else ""
            )


class ImgurApi:
    API_URL = "https://api.imgur.com/3"

    def __init__(self, client_id):
        self.client_id = client_id

    @defer.inlineCallbacks
    def _make_request(self, url):
        r = yield deferToThread(
            requests.get,
            url,
            headers={'Authorization': f'Client-ID {self.client_id}'},
        )

        r.raise_for_status()

        res = r.json()
        if not res['success']:
            raise Exception("Error during imgur request: {}", res)

        return res['data']

    @defer.inlineCallbacks
    def get_image(self, image_hash):
        return (yield self._make_request(
            f"{self.API_URL}/image/{image_hash}"))

    @defer.inlineCallbacks
    def get_album(self, album_hash):
        return (yield self._make_request(
            f"{self.API_URL}/albums/{album_hash}"))


entrypoint = ImgurPlugin
