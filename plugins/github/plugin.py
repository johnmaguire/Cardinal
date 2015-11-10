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

    default_repo = None
    """Default repository to select the issues from"""

    def __init__(self, cardinal, config):
        # Initialize logging
        self.logger = logging.getLogger(__name__)

        if config['default_repo']:
            self.default_repo = config['default_repo'].encode('utf8')

        self.callback_id = cardinal.event_manager.register_callback(
            'urls.detection', self._get_repo_info
        )

    def search(self, cardinal, user, channel, msg):
        # Grab the search query
        try:
            repo = msg.split(' ', 2)[1]

            if not REPO_NAME_REGEX.match(repo):
                if not self.default_repo:
                    cardinal.sendMsg(channel, "Syntax: .issue <user/repo> <id or search query>")
                    return

                repo = self.default_repo
                query = msg.split(' ', 1)[1]
            else:
                query = msg.split(' ', 2)[2]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .issue [repo] <id or search query>")
            return

        try:
            self._show_issue(cardinal, channel, repo, int(query))
        except ValueError:
            res = self._form_request('search/issues', {'q': "repo:%s %s" % (repo, query)})
            num = 0
            for issue in res['items']:
                cardinal.sendMsg(channel, self._format_issue(issue))
                if num == 4: break
                num += 1
            if res['total_count'] > 5:
                cardinal.sendMsg(channel, "...and %d more" % (res['total_count'] - 5))

    search.commands = ['issue']
    search.help = ["Find a Github repo or issue (or combination thereof)",
                   "Syntax: .issue [repo] <id or search query>"]

    def _format_issue(self, issue):
        message = "#%s: %s" % (issue['number'], issue['title'])
        if issue['state'] == 'closed':
            message = u'\u2713 ' + message
        elif issue['state'] == 'open':
            message = "! " + message
        if issue['assignee']:
            message += " @%s" % issue['assignee']['login']
        message += " " + issue['html_url']
        return message.encode('utf8')

    def _show_issue(self, cardinal, channel, repo, number):
        issue = self._form_request('repos/%s/issues/%d' % (repo, number))
        cardinal.sendMsg(channel, self._format_issue(issue))

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

    def _form_request(self, endpoint, params={}):
        # Make request to specified endpoint and return JSON decoded result
        uh = urllib2.urlopen("https://api.github.com/" +
            endpoint + "?" +
            urllib.urlencode(params))

        return json.load(uh)

    def close(self, cardinal):
        cardinal.event_manager.remove_callback('urls.detection', self.callback_id)

def setup(cardinal, config):
    return GithubPlugin(cardinal, config)
