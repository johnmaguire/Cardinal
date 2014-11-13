class CardinalException(Exception):
	"""This is the base class that all Cardinal exceptions extend."""
	pass

class InternalError(CardinalException):
	"""This is a non-recoverable error in the internals of Cardinal."""
	pass

class PluginError(CardinalException):
	"""This exception is raised when a plugin is invalid in some way."""
	pass

class CommandNotFoundError(CardinalException):
	"""This exception is raised when a given command isn't loaded."""
	pass
