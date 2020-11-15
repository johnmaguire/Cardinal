from builtins import object
import datetime

import pytest
from twisted.internet import defer

from cardinal import util


@pytest.mark.parametrize("input_,expected", (
    ('\x02bold\x02', 'bold'),
    ('\x0309colored\x03', 'colored'),
    # a naive implementation may return 45
    ('\x03\x033,012345', '2345'),
))
def test_strip_formatting(input_, expected):
    assert util.strip_formatting(input_) == expected


@defer.inlineCallbacks
def test_sleep():
    now = datetime.datetime.now()
    yield util.sleep(1)
    delta = datetime.datetime.now() - now
    assert delta.seconds == 1


class TestColors(object):
    @pytest.mark.parametrize('color,color_value', (
        ('white', 0),
        ('black', 1),
        ('blue', 2),
        ('green', 3),
        ('light_red', 4),
        ('brown', 5),
        ('purple', 6),
        ('orange', 7),
        ('yellow', 8),
        ('light_green', 9),
        ('cyan', 10),
        ('light_cyan', 11),
        ('light_blue', 12),
        ('pink', 13),
        ('grey', 14),
        ('light_grey', 15),
    ))
    def test_colors(self, color, color_value):
        text = 'sample message'

        f = getattr(util.F.C, color)

        # foreground color numbers must be zero-padded to a width of 2
        assert f(text) == '\x03{:02}{}\x03'.format(color_value, text)
