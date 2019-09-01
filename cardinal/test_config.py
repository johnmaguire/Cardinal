import pytest

from cardinal.config import ConfigSpec


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
