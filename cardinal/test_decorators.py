from __future__ import absolute_import, print_function, division

import pytest

from cardinal import decorators


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


@pytest.mark.parametrize("input,expected", [
    ('foo', 'foo'),
    (r'foo', r'foo'),
])
def test_regex(input, expected):
    # ensure events is a list with inputs added
    @decorators.regex(input)
    def regexCallback():
        pass

    assert regexCallback.regex == expected


def test_regex_overwrites():
    @decorators.regex('foo')
    @decorators.regex('bar')
    def foo():
        pass

    assert foo.regex == 'foo'


def test_regex_function_wrap():
    # test that the decorator doesn't break the function
    @decorators.regex('foo')
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
    {'foo': 'bar'},
    object(),
])
def test_regex_exceptions(value):
    # only allow strings and lists
    with pytest.raises(TypeError):
        @decorators.regex(value)
        def foo():
            pass


@pytest.mark.parametrize("input,expected", (
    (["A help line", "A second help line"],
     ["A help line", "A second help line"]),
    (["A single help line"], ["A single help line"]),
    ("A real single help line", ["A real single help line"]),
))
def test_help(input, expected):
    @decorators.help(input)
    def foo(x):
        return x

    # ensure help is a tuple with each param added
    assert foo.help == expected
    assert foo(1) == 1


def test_help_multiple_calls():
    @decorators.help("This is the first help line")
    @decorators.help("This is the second help line")
    def foo():
        pass

    # test the order of the help lines
    assert foo.help == [
        "This is the first help line",
        "This is the second help line",
    ]

@pytest.mark.parametrize("value", [
    True,
    False,
    5,
    3.14,
    ('foo',),
    {'foo': 'bar'},
    object(),
])
def test_help_exceptions(value):
    # only allow strings and lists
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


def test_event_overwrites():
    # test that only one decorator can add events
    @decorators.event('irc.privmsg')
    @decorators.event('irc.notice')
    def foo():
        pass

    assert foo.events == ['irc.privmsg']


def test_event_function_wrap():
    # test that the decorator doesn't break the function
    @decorators.event('foo')
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
    {'foo': 'bar'},
    object(),
])
def test_event_exceptions(value):
    # only allow strings and lists
    with pytest.raises(TypeError):
        @decorators.event(value)
        def foo():
            pass
