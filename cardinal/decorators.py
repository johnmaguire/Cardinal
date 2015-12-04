import functools

def command(triggers):
    if isinstance(triggers, basestring):
        triggers = [triggers]

    def wrap(f):
        @functools.wraps(f)
        def inner(*args, **kwargs):
            return f(*args, **kwargs)

        inner.commands = triggers
        return inner

    return wrap

def help(line):
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
