import re
import functools


_RETYPE = type(re.compile('foobar'))


def command(triggers):
    if isinstance(triggers, basestring):
        triggers = [triggers]

    if not isinstance(triggers, list):
        raise TypeError("Command must be a trigger string or list of triggers")

    def wrap(f):
        @functools.wraps(f)
        def inner(*args, **kwargs):
            return f(*args, **kwargs)

        inner.commands = triggers
        return inner

    return wrap


def regex(expression):
    if (not isinstance(expression, basestring) and
            not isinstance(expression, _RETYPE)):
        raise TypeError("Regular expression must be a string or regex type")

    def wrap(f):
        @functools.wraps(f)
        def inner(*args, **kwargs):
            return f(*args, **kwargs)

        inner.regex = expression
        return inner

    return wrap


def help(line):
    if not isinstance(line, basestring):
        raise TypeError("Help line must be a string")

    def wrap(f):
        @functools.wraps(f)
        def inner(*args, **kwargs):
            return f(*args, **kwargs)

        # Create help list or prepend to it
        if not hasattr(inner, 'help'):
            inner.help = [line]
        else:
            inner.help.insert(0, line)

        return inner

    return wrap


def event(triggers):
    if isinstance(triggers, basestring):
        triggers = [triggers]

    if not isinstance(triggers, list):
        raise TypeError("Event must be a trigger string or list of triggers")

    def wrap(f):
        @functools.wraps(f)
        def inner(*args, **kwargs):
            return f(*args, **kwargs)

        inner.events = triggers
        return inner

    return wrap
