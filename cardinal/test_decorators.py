import pytest

import decorators

def test_command():
    # ensure commands is a list with foo added
    @decorators.command('foo')
    def foo():
        pass

    assert foo.commands == ['foo']

    # test that you can pass a list
    @decorators.command(['foo', 'bar'])
    def foo():
        pass

    assert foo.commands == ['foo', 'bar']

    # test that only one decorator can add commands
    @decorators.command('foo')
    @decorators.command('bar')
    def foo():
        pass

    assert foo.commands == ['foo']

    # test that the decorator doesn't break the function
    @decorators.command('foo')
    def foo(bar, baz):
        return bar + baz

    assert foo(3, baz=4) == 7
    assert foo(5, 5) == 10

def test_command_exceptions():
    # only allow strings and lists
    with pytest.raises(TypeError):
        @decorators.command(True)
        def foo():
            pass

    with pytest.raises(TypeError):
        @decorators.command(5)
        def foo():
            pass

    with pytest.raises(TypeError):
        @decorators.command(('foo',))
        def foo():
            pass

def test_help():
    # ensure help is a list with the line added
    @decorators.help("This is a help line")
    def foo():
        pass

    assert foo.help == ["This is a help line"]

    # test the order of the help lines
    @decorators.help("This is the first help line")
    @decorators.help("This is the second help line")
    def foo():
        pass

    assert foo.help == [
        "This is the first help line",
        "This is the second help line",
    ]

    # test that the decorator doesn't break the function
    @decorators.help('foo')
    def foo(bar, baz):
        return bar + baz

    assert foo(3, baz=4) == 7
    assert foo(5, 5) == 10

def test_help_exceptions():
    # only allow strings
    with pytest.raises(TypeError):
        @decorators.help(["This should raise an exception"])
        def foo():
            pass

    with pytest.raises(TypeError):
        @decorators.help(5)
        def foo():
            pass

    with pytest.raises(TypeError):
        @decorators.help(True)
        def foo():
            pass

    with pytest.raises(TypeError):
        @decorators.help(('foo',))
        def foo():
            pass
