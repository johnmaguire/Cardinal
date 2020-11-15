from future import standard_library
standard_library.install_aliases()
from builtins import object
import re
import json
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import logging

from cardinal.decorators import command, event, help
from cardinal.exceptions import EventRejectedMessage

REPO_URL_REGEX = re.compile(
    r'https://(?:www\.)?github\..{2,4}/([^/]+)/([^/]+)',
    flags=re.IGNORECASE)
ISSUE_URL_REGEX = re.compile(
    r'https://(?:www\.)?github\..{2,4}/([^/]+)/([^/]+)/issues/([0-9]+)',
    flags=re.IGNORECASE)
REPO_NAME_REGEX = re.compile(
    r'^[a-z0-9-]+/[a-z0-9_-]+$',
    flags=re.IGNORECASE)


class GithubPlugin(object):
    logger = None
    """Logging object for GithubPlugin"""

    default_repo = None
    """Default repository to select the issues from"""

    max_show_issues = 1
    """Max number of issues to show for a search. -1 means all"""

    def __init__(self, cardinal, config):
        # Initialize logging
        self.logger = logging.getLogger(__name__)

        if 'default_repo' in config and config['default_repo']:
            self.default_repo = config['default_repo']

        if 'max_show_issues' in config and config['max_show_issues']:
            self.max_show_issues = config['max_show_issues']

    @command('issue')
    @help("Find a Github repo or issue (or combination thereof)")
    @help("Syntax: .issue [username/repository] <id or search query>")
    def search(self, cardinal, user, channel, msg):
        # Grab the search query
        try:
            repo = msg.split(' ', 2)[1]

            if not REPO_NAME_REGEX.match(repo):
                if not self.default_repo:
                    cardinal.sendMsg(
                        channel,
                        "Syntax: .issue <username/repository> <id or search "
                        "query>")
                    return

                repo = self.default_repo
                query = msg.split(' ', 1)[1]
            else:
                query = msg.split(' ', 2)[2]
        except IndexError:
            cardinal.sendMsg(
                channel,
                "Syntax: .issue [username/repository] <id or search query>")
            return

        try:
            self._show_issue(cardinal, channel, repo, int(query))
        except ValueError:
            res = self._form_request('search/issues',
                                     {'q': "repo:%s %s" % (repo, query)})
            num = 0
            for issue in res['items']:
                cardinal.sendMsg(channel, self._format_issue(issue))
                num += 1
                if num == self.max_show_issues:
                    break
            if res['total_count'] > self.max_show_issues:
                cardinal.sendMsg(channel,
                                 "...and %d more" %
                                 (res['total_count'] - self.max_show_issues))
            elif res['total_count'] == 0:
                cardinal.sendMsg(channel,
                                 "No matching issues found in %s" % repo)
        except urllib.error.HTTPError:
            cardinal.sendMsg(channel,
                             "Couldn't find %s#%d" % (repo, int(query)))

    @event('urls.detection')
    def get_repo_info(self, cardinal, channel, url):
        match = re.match(ISSUE_URL_REGEX, url)
        if not match:
            match = re.match(REPO_URL_REGEX, url)
        if not match:
            raise EventRejectedMessage

        groups = match.groups()
        try:
            if len(groups) == 3:
                self._show_issue(cardinal,
                                 channel,
                                 '%s/%s' % (groups[0], groups[1]),
                                 int(groups[2]))
            elif len(groups) == 2:
                self._show_repo(cardinal,
                                channel,
                                '%s/%s' % (groups[0], groups[1]))
        except urllib.error.HTTPError:
            raise EventRejectedMessage

    def _format_issue(self, issue):
        message = "#%s: %s" % (issue['number'], issue['title'])

        if issue['state'] == 'closed':
            message = u"\u2713 %s" % message
        elif issue['state'] == 'open':
            message = "! " + message

        if issue['assignee']:
            message += " @%s" % issue['assignee']['login']

        message += " " + issue['html_url']

        # Add labels, if there are any
        if issue['labels']:
            labels = ['[{}]'.format(label['name'])
                      for label in issue['labels']]
            message += ' ' + ' '.join(labels)

        return message

    def _show_issue(self, cardinal, channel, repo, number):
        issue = self._form_request('repos/%s/issues/%d' % (repo, number))
        cardinal.sendMsg(channel, self._format_issue(issue))

    def _show_repo(self, cardinal, channel, repo):
        repo = self._form_request('repos/' + repo)
        message = "[ %s - %s " % (repo['full_name'], repo['description'])
        if repo['stargazers_count'] > 0:
            message += u"| \u2605 %s stars " % repo['stargazers_count']

        if repo['forks_count'] > 0:
            message += u"| \u2934 %s forks " % repo['forks_count']

        if repo['open_issues_count'] > 0:
            message += "| ! %s open issues " % repo['open_issues_count']

        message += "]"

        cardinal.sendMsg(channel, message)

    def _form_request(self, endpoint, params={}):
        # Make request to specified endpoint and return JSON decoded result
        uh = urllib.request.urlopen("https://api.github.com/" +
                             endpoint + "?" +
                             urllib.parse.urlencode(params))

        return json.load(uh)


def setup(cardinal, config):
    return GithubPlugin(cardinal, config)
