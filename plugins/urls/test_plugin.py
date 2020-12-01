import re

import pytest

from . import plugin


class TestURLRegex(object):
    @staticmethod
    def assertFindUrl(message, url):
        m = plugin.get_urls(message)
        assert len(m) == 1
        assert m[0] == url

    @pytest.mark.parametrize("url,expected", [
        ["http://tiny.cc/PiratesLive", "http://tiny.cc/PiratesLive"],
        ["http://tiny.cc/PiratesLive\x0f", "http://tiny.cc/PiratesLive"],
        ["http://tiny.cc/PiratesLive\x0f\x0f", "http://tiny.cc/PiratesLive"],
        ["\x1fhttp://tiny.cc/PiratesLive\x0f", "http://tiny.cc/PiratesLive"],
        ["\x1f\x0f\x0fhttp://tiny.cc/PiratesLive\x0f", "http://tiny.cc/PiratesLive"],
        ["\x1f\x0f\x0fhttp://tiny.cc/PiratesLive", "http://tiny.cc/PiratesLive"],
    ])
    def test_url_cant_contain_control_characters(self, url, expected):
        self.assertFindUrl(url, expected)

    @pytest.mark.parametrize("url", [
        "http://google.com/",
        "http://google.google/",
        "google.google",
        "google.com",
        "https://google.com/",
        "https://mail.google.com/u/0",
        "http://tiny.cc/PiratesLive",
    ])
    def test_valid(self, url):
        self.assertFindUrl(url, url)
