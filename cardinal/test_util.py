import pytest

import util


@pytest.mark.parametrize("input_,expected", (
    ('\x02bold\x02', 'bold'),
    ('\x0309colored\x03', 'colored'),
    # a naive implementation may return 45
    ('\x03\x033,012345', '2345'),
))
def test_strip_formatting(input_, expected):
    assert util.strip_formatting(input_) == expected
