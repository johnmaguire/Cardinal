import os

import pytest

from cardinal.config import ConfigParser, ConfigSpec

FIXTURE_DIRECTORY = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
)


class TestConfigSpec(object):
    def setup_method(self):
        self.config_spec = ConfigSpec()

    @pytest.mark.parametrize("option", [
        ('name', basestring, 'default'),
        (u'name', basestring, None),
        (b'name', basestring, None),
        ('name', int, 3),
    ])
    def test_add_option(self, option):
        self.config_spec.add_option(option[0], option[1], option[2])

    def test_add_option_invalid_name(self):
        with pytest.raises(TypeError):
            self.config_spec.add_option(3, int)

    def test_add_option_invalid_type(self):
        with pytest.raises(TypeError):
            self.config_spec.add_option('name', 'string')

    def test_return_value_or_default_nonexistent(self):
        with pytest.raises(KeyError):
            self.config_spec.return_value_or_default('foobar', 30)

    def test_return_value_or_default_wrong_type(self):
        name = 'name'
        default = 'default'
        self.config_spec.add_option(name, basestring, default)
        assert self.config_spec.return_value_or_default(name, 3) == default

    def test_return_value_or_default_none(self):
        name = 'name'
        default = 'default'
        self.config_spec.add_option(name, basestring, default)
        assert self.config_spec.return_value_or_default(name, None) == default

    def test_return_value_or_default_value(self):
        name = 'name'
        default = 'default'
        self.config_spec.add_option(name, basestring, default)

        value = 'value'
        assert self.config_spec.return_value_or_default(name, value) == value


class TestConfigParser(object):
    def setup_method(self):
        config_spec = self.config_spec = ConfigSpec()
        config_spec.add_option("not_in_json", basestring)
        config_spec.add_option("string", basestring)
        config_spec.add_option("int", int)
        config_spec.add_option("bool", bool)
        config_spec.add_option("dict", dict)

        self.config_parser = ConfigParser(config_spec)

    def test_constructor(self):
        with pytest.raises(TypeError):
            ConfigParser("not a ConfigSpec")

    def test_load_config_nonexistent_file(self):
        # For some reason, this silently fails
        self.config_parser.load_config(
            os.path.join(FIXTURE_DIRECTORY, 'nonexistent.json'))

        # should all be set to defaults
        assert self.config_parser.config['string'] is None
        assert self.config_parser.config['int'] is None
        assert self.config_parser.config['bool'] is None
        assert self.config_parser.config['dict'] is None

    def test_load_config_invalid_file(self):
        # For some reason, this silently fails
        self.config_parser.load_config(
            os.path.join(FIXTURE_DIRECTORY, 'invalid-json-config.json'))

        # should all be set to defaults
        assert self.config_parser.config['string'] is None
        assert self.config_parser.config['int'] is None
        assert self.config_parser.config['bool'] is None
        assert self.config_parser.config['dict'] is None

    def test_load_config_picks_up_values(self):
        self.config_parser.load_config(
            os.path.join(FIXTURE_DIRECTORY, 'config.json'))

        assert self.config_parser.config['string'] == 'value'
        assert self.config_parser.config['int'] == 3
        assert self.config_parser.config['bool'] is False
        assert self.config_parser.config['dict'] == {
            'dict': {'string': 'value'},
            'list': ['foo', 'bar', 'baz'],
        }

        # This should get set to None when it's not found in the file
        assert self.config_parser.config['not_in_json'] is None

        # This was in the file but not the spec and should not appear in config
        assert 'ignored_string' not in self.config_parser.config

    def test_merge_argparse_args_into_config(self):
        class args:
            string = 'value'
            int = 3
            bool = False
            dict = {'foo': 'bar'}
            ignored_string = 'asdf'

        self.config_parser.merge_argparse_args_into_config(args)

        assert self.config_parser.config['string'] == 'value'
        assert self.config_parser.config['int'] == 3
        assert self.config_parser.config['bool'] is False
        assert self.config_parser.config['dict'] == {'foo': 'bar'}

        # defaults only get set by load_config, not
        # merge_argparse_args_into_config
        assert 'not_in_json' not in self.config_parser.config

        # This was in the file but not the spec and should not appear in config
        assert 'ignored_string' not in self.config_parser.config

    def test_merge_argparse_args_into_config_overwrites_config(self):
        self.config_parser.load_config(
            os.path.join(FIXTURE_DIRECTORY, 'config.json'))

        assert self.config_parser.config['string'] == 'value'
        assert self.config_parser.config['int'] == 3
        assert self.config_parser.config['bool'] is False
        assert self.config_parser.config['dict'] == {
            'dict': {'string': 'value'},
            'list': ['foo', 'bar', 'baz'],
        }

        class args:
            string = 'new_value'
            int = 5
            dict = {'foo': 'bar'}

        self.config_parser.merge_argparse_args_into_config(args)

        assert self.config_parser.config['string'] == 'new_value'
        assert self.config_parser.config['int'] == 5
        assert self.config_parser.config['bool'] is False  # no value to update
        assert self.config_parser.config['dict'] == {'foo': 'bar'}
