import json
import urllib
import urllib2

class YouTubePlugin(object):
    def search(self, cardinal, user, channel, msg):
        # Before we do anything, let's make sure we'll be able to query YouTube
        if not hasattr(cardinal.config['youtube'], 'API_KEY') or cardinal.config['youtube'].API_KEY == "API_KEY":
            cardinal.sendMsg(channel, "YouTube plugin is not configured correctly. Please set API key.")

        # Grab the search query
        try:
            search_query = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .youtube <search query>")
            return

        try:
            yt_request = {'part': 'snippet', 'q': search_query, 'maxResults': 1, 'key': cardinal.config['youtube'].API_KEY}
            uh = urllib2.urlopen("https://www.googleapis.com/youtube/v3/search?" + urllib.urlencode(yt_request))
            content = json.load(uh)
        except urllib2.URLError:
            cardinal.sendMsg(channel, "Error accessing YouTube API. (URLError Exception occurred.)")
            return
        except urllib2.HTTPError:
            cardinal.sendMsg(channel, "Error accessing YouTube API. (HTTPError Exception occurred.")
            return

        if 'error' in content:
            cardinal.sendMsg(channel, "An error occurred while attempting to search YouTube.")
            print >> sys.stderr, "ERROR: Error attempting to search YouTube (%s)" % uh
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

def setup():
    return YouTubePlugin()
