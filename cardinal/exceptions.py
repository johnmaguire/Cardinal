class CardinalException(Exception):
	"""Base class that all Cardinal exceptions extend."""
	pass

class InternalError(CardinalException):
	"""Non-recoverable error in the internals of Cardinal."""
	pass

class PluginError(CardinalException):
	"""Raised when a plugin is invalid in some way."""
	pass

class CommandNotFoundError(CardinalException):
	"""Raised when a given command isn't loaded."""
	pass

class ConfigNotFoundError(CardinalException):
	"""Raised when an expected plugin config isn't found."""

class AmbiguousConfigError(CardinalException):
	"""Raised when multiple configs exist for a plugin."""

class EventAlreadyExistsError(CardinalException):
	"""Raised durring attempt to register an event name already registered."""

class EventDoesNotExistError(CardinalException):
	"""Raised during attempt to register a callback for a nonexistent event."""

class EventCallbackError(CardinalException):
	"""Raised when there is an error with a callback."""

class EventRejectedMessage(CardinalException):
	"""Raised when an event callback wants to reject an event."""
