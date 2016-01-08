import pytest

import decorators

@pytest.mark.parametrize("input,expected", [
    ('foo', ['foo']),
    (['foo'], ['foo']),
    (['foo', 'bar'], ['foo', 'bar']),
])
def test_command(input, expected):
    # ensure commands is a list with foo added
    @decorators.command(input)
    def foo():
        pass

    assert foo.commands == expected


def test_command_overwrites():
    # test that only one decorator can add commands
    @decorators.command('foo')
    @decorators.command('bar')
    def foo():
        pass

    assert foo.commands == ['foo']


def test_command_function_wrap():
    # test that the decorator doesn't break the function
    @decorators.command('foo')
    def foo(bar, baz):
        return bar + baz
    {'foo': 'bar'},

    assert foo(3, baz=4) == 7
    assert foo(5, 5) == 10


@pytest.mark.parametrize("value", [
    True,
    False,
    5,
    3.14,
    ('foo',),
    {'foo': 'bar'},
    object(),
])
def test_command_exceptions(value):
    # only allow strings and lists
    with pytest.raises(TypeError):
        @decorators.command(value)
        def foo():
            pass


def test_help():
    # ensure help is a list with the line added
    @decorators.help("This is a help line")
    def foo():
        pass

    assert foo.help == ["This is a help line"]


def test_help_order():
    # test the order of the help lines
    @decorators.help("This is the first help line")
    @decorators.help("This is the second help line")
    def foo():
        pass

    assert foo.help == [
        "This is the first help line",
        "This is the second help line",
    ]


def test_help_function_wrap():
    # test that the decorator doesn't break the function
    @decorators.help('foo')
    def foo(bar, baz):
        return bar + baz

    assert foo(3, baz=4) == 7
    assert foo(5, 5) == 10


@pytest.mark.parametrize("value", [
    True,
    False,
    5,
    3.14,
    ('foo',),
    ["This should raise an exception"],
    {'foo': 'bar'},
    object(),
])
def test_help_exceptions(value):
    # only allow strings
    with pytest.raises(TypeError):
        @decorators.help(value)
        def foo():
            pass

@pytest.mark.parametrize("input,expected", [
    ('irc.privmsg', ['irc.privmsg']),
    (['irc.privmsg'], ['irc.privmsg']),
    (['irc.privmsg', 'irc.notice'], ['irc.privmsg', 'irc.notice']),
])
def test_event(input, expected):
    # ensure events is a list with inputs added
    @decorators.event(input)
    def eventCallback():
        pass

    assert eventCallback.events == expected

def test_events_overwrites():
    # test that only one decorator can add events
    @decorators.event('irc.privmsg')
    @decorators.event('irc.notice')
    def foo():
        pass

    assert foo.events == ['irc.privmsg']

def test_command_function_wrap():
    # test that the decorator doesn't break the function
    @decorators.event('foo')
    def foo(bar, baz):
        return bar + baz
    {'foo': 'bar'},

    assert foo(3, baz=4) == 7
    assert foo(5, 5) == 10

@pytest.mark.parametrize("value", [
    True,
    False,
    5,
    3.14,
    ('foo',),
    {'foo': 'bar'},
    object(),
])
def test_event_exceptions(value):
    # only allow strings and lists
    with pytest.raises(TypeError):
        @decorators.event(value)
        def foo():
            pass
