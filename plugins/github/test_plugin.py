import requests
import pytest
import pytest_twisted
from unittest.mock import Mock, patch

from cardinal.exceptions import EventRejectedMessage
from plugins.github.plugin import GithubPlugin, COMMIT_URL_REGEX


def mock_response(json_body):
    response = Mock()
    response.json.return_value = json_body
    response.raise_for_status.return_value = None
    return response


class TestGithubPlugin:
    def setup_method(self):
        self.cardinal = Mock()
        self.plugin = GithubPlugin(self.cardinal, {})

    @pytest.mark.parametrize("url,expected", [
        ("https://github.com/user/repo/commit/"
         "29e3d9e94ae3fec6c2c9b15ef367cad293e4c362",
         ("user", "repo", "29e3d9e94ae3fec6c2c9b15ef367cad293e4c362")),
        ("https://www.github.com/user/repo/commit/abc123",
         ("user", "repo", "abc123")),
        ("https://github.io/user/repo/commit/def456",
         ("user", "repo", "def456")),
    ])
    def test_commit_url_regex(self, url, expected):
        match = COMMIT_URL_REGEX.match(url)
        assert match is not None
        assert match.groups() == expected

    @pytest.mark.parametrize("url", [
        "https://github.com/user/repo",
        "https://github.com/user/repo/issues/123",
        "https://github.com/user/repo/pull/456",
        "https://github.com/user/repo/commits/master",
        "https://example.com/user/repo/commit/abc",
    ])
    def test_commit_url_regex_no_match(self, url):
        match = COMMIT_URL_REGEX.match(url)
        assert match is None

    @pytest_twisted.inlineCallbacks
    def test_get_repo_info_commit(self):
        url = ("https://github.com/user/repo/commit/"
               "29e3d9e94ae3fec6c2c9b15ef367cad293e4c362")
        channel = "#test"

        commit = {
            'sha': '29e3d9e94ae3fec6c2c9b15ef367cad293e4c362',
            'commit': {
                'message': 'Fix bug in plugin\n\nThis fixes a critical bug.'
            },
            'stats': {
                'additions': 10,
                'deletions': 5
            }
        }

        with patch('requests.get', return_value=mock_response(commit)) \
                as mock_get:
            yield self.plugin.get_repo_info(self.cardinal, channel, url)

        assert mock_get.call_args[0][0] == \
            ("https://api.github.com/repos/user/repo/commits/"
             "29e3d9e94ae3fec6c2c9b15ef367cad293e4c362")
        self.cardinal.sendMsg.assert_called_once_with(
            channel, '29e3d9e: Fix bug in plugin (+10 -5)')

    @pytest_twisted.inlineCallbacks
    def test_get_repo_info_commit_no_stats(self):
        # stats may be omitted for very large diffs
        url = "https://github.com/user/repo/commit/abc123"
        channel = "#test"

        commit = {
            'sha': 'abc123def',
            'commit': {
                'message': 'Update README'
            }
        }

        with patch('requests.get', return_value=mock_response(commit)):
            yield self.plugin.get_repo_info(self.cardinal, channel, url)

        self.cardinal.sendMsg.assert_called_once_with(
            channel, 'abc123d: Update README')

    @pytest_twisted.inlineCallbacks
    def test_get_repo_info_commit_http_error(self):
        url = "https://github.com/user/repo/commit/deadbeef"
        channel = "#test"

        response = Mock()
        response.raise_for_status.side_effect = \
            requests.exceptions.HTTPError()

        with patch('requests.get', return_value=response):
            with pytest.raises(EventRejectedMessage):
                yield self.plugin.get_repo_info(self.cardinal, channel, url)

        assert not self.cardinal.sendMsg.called

    @pytest_twisted.inlineCallbacks
    def test_get_repo_info_unrecognized_url(self):
        url = "https://example.com/user/repo/commit/abc"
        channel = "#test"

        with pytest.raises(EventRejectedMessage):
            yield self.plugin.get_repo_info(self.cardinal, channel, url)

        assert not self.cardinal.sendMsg.called

    @pytest_twisted.inlineCallbacks
    def test_get_repo_info_repo_fallback(self):
        url = "https://github.com/user/repo"
        channel = "#test"

        repo = {
            'full_name': 'user/repo',
            'description': 'A test repo',
            'stargazers_count': 100,
            'forks_count': 20,
            'open_issues_count': 5
        }

        with patch('requests.get', return_value=mock_response(repo)):
            yield self.plugin.get_repo_info(self.cardinal, channel, url)

        self.cardinal.sendMsg.assert_called_once_with(
            channel,
            u"[ user/repo - A test repo | ★ 100 stars "
            u"| ⤴ 20 forks | ! 5 open issues ]")

    @pytest_twisted.inlineCallbacks
    def test_get_repo_info_issue(self):
        url = "https://github.com/user/repo/issues/123"
        channel = "#test"

        issue = {
            'number': 123,
            'title': 'Test issue',
            'state': 'open',
            'assignee': None,
            'labels': [{'name': 'bug'}],
            'html_url': 'https://github.com/user/repo/issues/123'
        }

        with patch('requests.get', return_value=mock_response(issue)):
            yield self.plugin.get_repo_info(self.cardinal, channel, url)

        self.cardinal.sendMsg.assert_called_once_with(
            channel,
            "! #123: Test issue - https://github.com/user/repo/issues/123 "
            "[bug]")
