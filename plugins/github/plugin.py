import re
import json
import urllib
import urllib2
import logging

from cardinal.exceptions import EventRejectedMessage

REPO_URL_REGEX  = re.compile(r'https://(?:www\.)?github\..{2,4}/([^/]+)(?:/([^/]+))?', flags=re.IGNORECASE)
ISSUE_URL_REGEX = re.compile(r'https://(?:www\.)?github\..{2,4}/([^/]+)/([^/]+)/issues/([0-9]+)', flags=re.IGNORECASE)
REPO_NAME_REGEX = re.compile(r'^[a-z0-9-]+/[a-z0-9_-]+$', flags=re.IGNORECASE)

class GithubPlugin(object):
    logger = None
    """Logging object for YouTubePlugin"""

    def __init__(self, cardinal):
        # Initialize logging
        self.logger = logging.getLogger(__name__)

        self.callback_id = cardinal.event_manager.register_callback(
            'urls.detection', self._get_repo_info
        )

    def search(self, cardinal, user, channel, msg):
        # Grab the search query
        try:
            repo = msg.split(' ', 2)[1]

            if not REPO_NAME_REGEX.match(repo):
                repo = "JohnMaguire/Cardinal" # @TODO: config.json
                query = msg.split(' ', 1)[1]
            else:
                query = msg.split(' ', 2)[2]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .issue [repo] <id or search query>")
            return

        try:
            self._show_issue(cardinal, channel, repo, int(query))
        except ValueError:
            cardinal.sendMsg(channel, "Searching for '%s' in %s" % (query, repo))

    search.commands = ['issue']
    search.help = ["Find a Github repo or issue (or combination thereof)",
                   "Syntax: .issue [repo] <id or search query>"]

    def _show_issue(self, cardinal, channel, repo, id):
        cardinal.sendMsg(channel, "show %s#%d" % (repo, id))

    def _show_repo(self, cardinal, channel, repo):
        cardinal.sendMsg(channel, "show repo %s" % repo)

    def _show_user(self, cardinal, channel, user):
        cardinal.sendMsg(channel, "show user %s" % user)

    def _get_repo_info(self, cardinal, channel, url):
        match = re.match(ISSUE_URL_REGEX, url)
        if not match:
            match = re.match(REPO_URL_REGEX, url)
        if not match:
            raise EventRejectedMessage

        groups = match.groups()
        if len(groups) == 3:
            self._show_issue(cardinal, channel, '%s/%s' % (groups[0], groups[1]), int(groups[2]))
        elif len(groups) == 2:
            self._show_repo(cardinal, channel, '%s/%s' % (groups[0], groups[1]))
        elif len(groups) == 1:
            self._show_user(cardinal, channel, groups[1])

    def _form_request(self, endpoint, params):
        # Make request to specified endpoint and return JSON decoded result
        uh = urllib2.urlopen("https://api.github.com/" +
            endpoint + "?" +
            urllib.urlencode(params))

        return json.load(uh)

    def close(self, cardinal):
        cardinal.event_manager.remove_callback('urls.detection', self.callback_id)

def setup(cardinal):
    return GithubPlugin(cardinal)
