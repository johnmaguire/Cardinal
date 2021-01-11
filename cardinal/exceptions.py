from __future__ import absolute_import, print_function, division


class CardinalException(Exception):
    """Base class that all Cardinal exceptions extend."""


class LockInUseError(CardinalException):
    """Raised when a lock is unavailable."""


class PluginError(CardinalException):
    """Raised when a plugin is invalid in some way."""


class CommandNotFoundError(CardinalException):
    """Raised when a given command isn't loaded."""


class ConfigNotFoundError(CardinalException):
    """Raised when an expected plugin config isn't found."""


class EventAlreadyExistsError(CardinalException):
    """Raised durring attempt to register an event name already registered."""


class EventDoesNotExistError(CardinalException):
    """Raised during attempt to register a callback for a nonexistent event."""


class EventCallbackError(CardinalException):
    """Raised when there is an error with a callback."""


class EventRejectedMessage(CardinalException):
    """Raised when an event callback wants to reject an event."""
