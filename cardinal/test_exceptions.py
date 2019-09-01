from __future__ import absolute_import, print_function, division

import pytest

from cardinal import exceptions


def test_exceptions():
    # testing exception inheritance
    with pytest.raises(Exception):
        raise exceptions.CardinalException

    with pytest.raises(exceptions.CardinalException):
        raise exceptions.InternalError

    with pytest.raises(exceptions.CardinalException):
        raise exceptions.PluginError

    with pytest.raises(exceptions.CardinalException):
        raise exceptions.CommandNotFoundError

    with pytest.raises(exceptions.CardinalException):
        raise exceptions.ConfigNotFoundError

    with pytest.raises(exceptions.CardinalException):
        raise exceptions.EventAlreadyExistsError

    with pytest.raises(exceptions.CardinalException):
        raise exceptions.EventDoesNotExistError

    with pytest.raises(exceptions.CardinalException):
        raise exceptions.EventCallbackError

    with pytest.raises(exceptions.CardinalException):
        raise exceptions.EventRejectedMessage
