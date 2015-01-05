import json
import urllib
import urllib2
import logging


class YouTubePlugin(object):
    logger = None
    """Logging object for YouTubePlugin"""

    api_key = None
    """API key for Youtube API"""

    def __init__(self, cardinal, config):
        # Initialize logging
        self.logger = logging.getLogger(__name__)

        if config is None:
            return

        if 'api_key' in config:
            self.api_key = config['api_key']

    def search(self, cardinal, user, channel, msg):
        # Before we do anything, let's make sure we'll be able to query YouTube
        if self.api_key is None:
            cardinal.sendMsg(channel, "YouTube plugin is not configured correctly. Please set API key.")

        # Grab the search query
        try:
            search_query = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .youtube <search query>")
            return

        try:
            yt_request = {'part': 'snippet', 'q': search_query, 'maxResults': 1, 'key': self.api_key}
            uh = urllib2.urlopen("https://www.googleapis.com/youtube/v3/search?" + urllib.urlencode(yt_request))
            content = json.load(uh)
        except Exception, e:
            cardinal.sendMsg(channel, "Unable to connect to YouTube.")
            self.logger.exception("Failed to connect to YouTube")
            return

        if 'error' in content:
            cardinal.sendMsg(channel, "An error occurred while attempting to search YouTube.")
            self.logger.error(
                "Error attempting to search YouTube: %s" % content['error']
            )
            return

        try:
            title = content['items'][0]['snippet']['title']
            uploader = content['items'][0]['snippet']['channelTitle']
            if len(uploader) == 0:
                uploader = "(not available)"
            video_id = content['items'][0]['id']['videoId']

            cardinal.sendMsg(channel, "[ Title: %s | Uploaded by: %s | https://www.youtube.com/watch?v=%s ]" % (str(title), str(uploader), str(video_id)))
        except IndexError:
            cardinal.sendMsg(channel, "No videos found matching that search.")

    search.commands = ['youtube', 'yt']
    search.help = ["Get the first YouTube result for a given search.",
                   "Syntax: .youtube <search query>"]

def setup(cardinal, config):
    return YouTubePlugin(cardinal, config)
