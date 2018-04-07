import inspect
import os
import sys

from mock import Mock, patch
import pytest

from bot import CardinalBot
from exceptions import AmbiguousConfigError
from plugins import PluginManager

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
FIXTURE_PATH = os.path.join(DIR_PATH, 'fixtures')
sys.path.insert(0, FIXTURE_PATH)


class TestPluginManager(object):
    def test_constructor_no_plugins(self):
        manager = PluginManager(Mock())
        assert len(manager.plugins) == 0

    def test_constructor_no_plugins_empty_list(self):
        manager = PluginManager(Mock(), [])
        assert len(manager.plugins) == 0

    @patch.object(PluginManager, 'load')
    def test_constructor_loads_plugins(self, mock):
        plugins = ['foo', 'bar']
        PluginManager(Mock(), plugins)
        mock.assert_called_with(plugins)

    @pytest.mark.parametrize("plugins", [
        'a string',
        12345,
        0.0,
        object(),
    ])
    def test_constructor_plugins_not_a_list_typeerror(self, plugins):
        with pytest.raises(TypeError):
            PluginManager(Mock(), plugins)

    @pytest.mark.parametrize("plugins", [
        12345,
        0.0,
        object(),
    ])
    def test_load_plugins_not_a_list_or_string_typeerror(self, plugins):
        manager = PluginManager(Mock())
        with pytest.raises(TypeError):
            manager.load(plugins)

    def test_load_nonexistent_plugin_fails(self):
        name = 'nonexistent'
        plugins = [name]

        manager = PluginManager(Mock())
        failed_plugins = manager.load(plugins)
        assert failed_plugins == plugins
        assert manager.plugins == {}

    def test_load_no_setup_fails(self):
        name = 'no_setup'
        plugins = [name]

        manager = PluginManager(Mock(),
                                _plugin_module_import_prefix='fake_plugins')

        failed_plugins = manager.load(plugins)
        assert failed_plugins == plugins
        assert manager.plugins.keys() == []

    def test_load_setup_too_many_arguments_fails(self):
        name = 'setup_too_many_arguments'
        plugins = [name]

        manager = PluginManager(Mock(),
                                _plugin_module_import_prefix='fake_plugins')

        failed_plugins = manager.load(plugins)
        assert failed_plugins == plugins
        assert manager.plugins.keys() == []

    def test_load_valid_list(self):
        name = 'valid'
        plugins = [name]

        manager = PluginManager(Mock(),
                                _plugin_module_import_prefix='fake_plugins')

        failed_plugins = manager.load(plugins)
        assert failed_plugins == []
        assert manager.plugins.keys() == plugins

        assert manager.plugins[name]['name'] == name
        assert inspect.ismodule(manager.plugins[name]['module'])
        assert isinstance(manager.plugins[name]['instance'],
                          manager.plugins[name]['module'].TestValidPlugin)
        assert manager.plugins[name]['commands'] == []
        assert manager.plugins[name]['callbacks'] == []
        assert manager.plugins[name]['callback_ids'] == {}
        assert manager.plugins[name]['config'] is None
        assert manager.plugins[name]['blacklist'] == []

    def test_load_valid_string(self):
        name = 'valid'
        plugins = [name]

        manager = PluginManager(Mock(),
                                _plugin_module_import_prefix='fake_plugins')

        failed_plugins = manager.load(name)
        assert failed_plugins == []
        assert manager.plugins.keys() == plugins

        assert manager.plugins[name]['name'] == name
        assert inspect.ismodule(manager.plugins[name]['module'])
        assert isinstance(manager.plugins[name]['instance'],
                          manager.plugins[name]['module'].TestValidPlugin)
        assert manager.plugins[name]['commands'] == []
        assert manager.plugins[name]['callbacks'] == []
        assert manager.plugins[name]['callback_ids'] == {}
        assert manager.plugins[name]['config'] is None
        assert manager.plugins[name]['blacklist'] == []

    @patch.object(PluginManager, '_load_plugin_config')
    def test_load_ambiguous_config_fails(self, mock):
        name = 'valid'
        plugins = [name]

        manager = PluginManager(Mock(),
                                _plugin_module_import_prefix='fake_plugins')
        mock.side_effect = AmbiguousConfigError()

        failed_plugins = manager.load(plugins)

        mock.assert_called_with(name)
        assert failed_plugins == plugins
        assert manager.plugins == {}

    @patch.object(PluginManager, '_register_plugin_callbacks')
    def test_load_bad_callback_fails(self, mock):
        name = 'valid'
        plugins = [name]

        manager = PluginManager(Mock(),
                                _plugin_module_import_prefix='fake_plugins')
        mock.side_effect = Exception()

        failed_plugins = manager.load(plugins)

        assert failed_plugins == plugins
        assert manager.plugins == {}

    def test_reload_valid_succeeds(self):
        name = 'reload_valid'
        plugins = [name]

        cardinal = Mock(CardinalBot)
        cardinal.reloads = 0

        manager = PluginManager(cardinal,
                                _plugin_module_import_prefix='fake_plugins')

        failed_plugins = manager.load(plugins)
        assert failed_plugins == []
        assert manager.plugins.keys() == plugins

        failed_plugins = manager.load(plugins)
        assert failed_plugins == []
        assert manager.plugins.keys() == plugins

        assert cardinal.reloads == 1

    def test_reload_unclean_close_succeeds(self):
        name = 'unclean_close'
        plugins = [name]

        cardinal = Mock(CardinalBot)
        cardinal.reloads = 0

        manager = PluginManager(cardinal,
                                _plugin_module_import_prefix='fake_plugins')

        failed_plugins = manager.load(plugins)
        assert failed_plugins == []
        assert manager.plugins.keys() == plugins

        failed_plugins = manager.load(plugins)
        assert failed_plugins == []
        assert manager.plugins.keys() == plugins

        assert cardinal.reloads == 1

    @pytest.mark.parametrize("plugins", [
        12345,
        0.0,
        object(),
    ])
    def test_unload_plugins_not_a_list_or_string_typeerror(self, plugins):
        manager = PluginManager(Mock())
        with pytest.raises(TypeError):
            manager.unload(plugins)

    def test_unload_plugins_never_loaded_plugin_fails(self):
        name = 'test_never_loaded_plugin'
        plugins = [name]

        manager = PluginManager(Mock())
        failed_plugins = manager.unload(plugins)

        assert failed_plugins == plugins
        assert manager.plugins == {}

    def test_unload_unclean_close_fails(self):
        name = 'unclean_close'
        plugins = [name]

        manager = PluginManager(Mock(),
                                _plugin_module_import_prefix='fake_plugins')

        failed_plugins = manager.load(plugins)
        assert failed_plugins == []
        assert manager.plugins.keys() == plugins

        failed_plugins = manager.unload(plugins)

        assert failed_plugins == plugins
        assert manager.plugins == {}

    def test_unload_valid_succeeds(self):
        name = 'valid'
        plugins = [name]

        manager = PluginManager(Mock(),
                                _plugin_module_import_prefix='fake_plugins')

        failed_plugins = manager.load(plugins)
        assert failed_plugins == []
        assert manager.plugins.keys() == plugins

        failed_plugins = manager.unload(plugins)

        assert failed_plugins == []
        assert manager.plugins.keys() == []

        name = 'test_valid_plugin'
        plugins = [name]

    def test_unload_clean_close_succeeds(self):
        name = 'clean_close'
        plugins = [name]

        manager = PluginManager(Mock(),
                                _plugin_module_import_prefix='fake_plugins')

        failed_plugins = manager.load(plugins)
        assert failed_plugins == []
        assert manager.plugins.keys() == plugins

        failed_plugins = manager.unload(plugins)

        assert failed_plugins == []
        assert manager.plugins.keys() == []

    @patch.object(PluginManager, '_unregister_plugin_callbacks')
    def test_unload_unregister_plugin_callbacks_error_succeeds(self, mock):
        name = 'clean_close'
        plugins = [name]

        manager = PluginManager(Mock(),
                                _plugin_module_import_prefix='fake_plugins')

        failed_plugins = manager.load(plugins)
        assert failed_plugins == []
        assert manager.plugins.keys() == plugins

        mock.side_effect = Exception()
        failed_plugins = manager.unload(plugins)

        assert failed_plugins == []
        assert manager.plugins.keys() == []

        mock.assert_called_with(name)
