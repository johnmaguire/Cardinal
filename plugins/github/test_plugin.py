import pytest
from unittest.mock import Mock, patch
from twisted.internet import defer

from plugins.github.plugin import GithubPlugin, COMMIT_URL_REGEX


class TestGithubPlugin:
    def setup_method(self):
        self.cardinal = Mock()
        self.cardinal.sendMsg = Mock()
        self.plugin = GithubPlugin(self.cardinal, {})

    @pytest.mark.parametrize("url,expected", [
        ("https://github.com/user/repo/commit/29e3d9e94ae3fec6c2c9b15ef367cad293e4c362", ("user", "repo", "29e3d9e94ae3fec6c2c9b15ef367cad293e4c362")),
        ("https://www.github.com/user/repo/commit/abc123", ("user", "repo", "abc123")),
        ("https://github.io/user/repo/commit/def456", ("user", "repo", "def456")),
    ])
    def test_commit_url_regex(self, url, expected):
        match = COMMIT_URL_REGEX.match(url)
        assert match is not None
        assert match.groups() == expected

    @pytest.mark.parametrize("url", [
        "https://github.com/user/repo",
        "https://github.com/user/repo/issues/123",
        "https://github.com/user/repo/pull/456",
        "https://example.com/user/repo/commit/abc",
    ])
    def test_commit_url_regex_no_match(self, url):
        match = COMMIT_URL_REGEX.match(url)
        assert match is None

    @pytest.inlineCallbacks
    def test_get_repo_info_commit(self):
        url = "https://github.com/user/repo/commit/29e3d9e94ae3fec6c2c9b15ef367cad293e4c362"
        channel = "#test"

        mock_commit = {
            'sha': '29e3d9e94ae3fec6c2c9b15ef367cad293e4c362',
            'commit': {
                'message': 'Fix bug in plugin\n\nThis fixes a critical bug.'
            },
            'stats': {
                'additions': 10,
                'deletions': 5
            }
        }

        mock_response = Mock()
        mock_response.json.return_value = mock_commit
        mock_response.raise_for_status.return_value = None

        with patch('requests.get', return_value=mock_response):
            yield self.plugin.get_repo_info(self.cardinal, channel, url)

            self.cardinal.sendMsg.assert_called_once_with(channel, '29e3d9e: Fix bug in plugin (+10 -5)')

    @pytest.inlineCallbacks
    def test_get_repo_info_commit_no_stats(self):
        url = "https://github.com/user/repo/commit/abc123"
        channel = "#test"

        mock_commit = {
            'sha': 'abc123def',
            'commit': {
                'message': 'Update README'
            }
        }

        mock_response = Mock()
        mock_response.json.return_value = mock_commit
        mock_response.raise_for_status.return_value = None

        with patch('requests.get', return_value=mock_response):
            yield self.plugin.get_repo_info(self.cardinal, channel, url)

            self.cardinal.sendMsg.assert_called_once_with(channel, 'abc123d: Update README')

    @pytest.inlineCallbacks
    def test_get_repo_info_repo_fallback(self):
        url = "https://github.com/user/repo"
        channel = "#test"

        mock_repo = {
            'full_name': 'user/repo',
            'description': 'A test repo',
            'stargazers_count': 100,
            'forks_count': 20,
            'open_issues_count': 5
        }

        mock_response = Mock()
        mock_response.json.return_value = mock_repo
        mock_response.raise_for_status.return_value = None

        with patch('requests.get', return_value=mock_response):
            yield self.plugin.get_repo_info(self.cardinal, channel, url)

            expected_msg = "[ user/repo - A test repo | ★ 100 stars | ⤴ 20 forks | ! 5 open issues ]"
            self.cardinal.sendMsg.assert_called_once_with(channel, expected_msg)

    @pytest.inlineCallbacks
    def test_get_repo_info_issue(self):
        url = "https://github.com/user/repo/issues/123"
        channel = "#test"

        mock_issue = {
            'number': 123,
            'title': 'Test issue',
            'state': 'open',
            'assignee': None,
            'labels': [{'name': 'bug'}],
            'html_url': 'https://github.com/user/repo/issues/123'
        }

        mock_response = Mock()
        mock_response.json.return_value = mock_issue
        mock_response.raise_for_status.return_value = None

        with patch('requests.get', return_value=mock_response):
            yield self.plugin.get_repo_info(self.cardinal, channel, url)

            expected_msg = "! #123: Test issue - https://github.com/user/repo/issues/123 [bug]"
            self.cardinal.sendMsg.assert_called_once_with(channel, expected_msg)