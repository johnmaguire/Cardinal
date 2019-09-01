from __future__ import absolute_import, print_function, division

import inspect
import logging
import os
import sys

from twisted.internet.task import defer
from mock import Mock, patch
import pytest

from cardinal import exceptions
from cardinal.bot import CardinalBot
from cardinal.plugins import EventManager, PluginManager

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
FIXTURE_PATH = os.path.join(DIR_PATH, 'fixtures')
sys.path.insert(0, FIXTURE_PATH)


class TestPluginManager(object):
    def setup_method(self):
        mock_cardinal = self.cardinal = Mock(spec=CardinalBot)
        mock_cardinal.event_manager = self.event_manager = \
            EventManager(mock_cardinal)

        self.plugin_manager = PluginManager(
            mock_cardinal,
            _plugin_module_import_prefix='fake_plugins',
            _plugin_module_directory_suffix='cardinal/fixtures/fake_plugins')

    def assert_load_success(self,
                            plugins,
                            assert_callbacks_is_empty=True,
                            assert_config_is_none=True):
        failed_plugins = self.plugin_manager.load(plugins)

        # regardless of the whether plugins was a string or list, the rest of
        # this function requires it to be a list
        if not isinstance(plugins, list):
            plugins = [plugins]

        assert failed_plugins == []
        assert len(self.plugin_manager.plugins.keys()) == len(plugins)

        for name in plugins:
            # class name for plugins must be Test(CamelCaseName)Plugin
            # e.g. an_example -> TestAnExamplePlugin
            class_ = 'Test'
            name_pieces = name.split('_')
            for name_piece in name_pieces:
                class_ += name_piece[0].upper() + name_piece[1:].lower()
            class_ += 'Plugin'

            # check that everything was set correctly
            assert name in self.plugin_manager.plugins.keys()
            assert self.plugin_manager.plugins[name]['name'] == name
            assert inspect.ismodule(
                self.plugin_manager.plugins[name]['module'])
            assert isinstance(
                self.plugin_manager.plugins[name]['instance'],
                getattr(self.plugin_manager.plugins[name]['module'],
                        class_))
            assert self.plugin_manager.plugins[name]['commands'] == []
            if assert_callbacks_is_empty:
                assert self.plugin_manager.plugins[name]['callbacks'] == []
                assert self.plugin_manager.plugins[name]['callback_ids'] == {}
            if assert_config_is_none:
                assert self.plugin_manager.plugins[name]['config'] is None
            assert self.plugin_manager.plugins[name]['blacklist'] == []

    def assert_load_failed(self, plugins):
        failed_plugins = self.plugin_manager.load(plugins)

        # regardless of the whether plugins was a string or list, the rest of
        # this function requires it to be a list
        if not isinstance(plugins, list):
            plugins = [plugins]

        assert failed_plugins == plugins
        assert self.plugin_manager.plugins == {}

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
        with pytest.raises(TypeError):
            self.plugin_manager.load(plugins)

    @pytest.mark.parametrize("plugins", [
        # This plugin won't be found in the plugins directory
        'nonexistent',
        # This plugin is missing a setup() function
        'setup_missing',
        # This plugin's setup() function takes three arguments
        'setup_too_many_arguments',
        # This plugin has both a config.yaml and config.json
        'config_ambiguous',
    ])
    def test_load_invalid(self, plugins):
        self.assert_load_failed(plugins)

    @pytest.mark.parametrize("plugins", [
        'valid',
        ['valid'],  # test list format
    ])
    def test_load_valid(self, plugins):
        self.assert_load_success(plugins)

    def test_load_cardinal_passed(self):
        name = 'setup_one_argument'
        self.assert_load_success(name)
        assert self.plugin_manager.plugins[name]['module'].cardinal is \
            self.cardinal

    def test_load_config_passed(self):
        name = 'setup_two_arguments'
        self.assert_load_success(name, assert_config_is_none=False)
        assert self.plugin_manager.plugins[name]['module'].cardinal is \
            self.cardinal
        assert self.plugin_manager.plugins[name]['module'].config == \
            {'test': True}

    def test_load_invalid_json_config(self):
        name = 'config_invalid_json'
        self.assert_load_success(name)  # no error for some reason

        # invalid json should be ignored
        assert self.plugin_manager.plugins[name]['config'] is None

    def test_load_invalid_yaml_config(self):
        name = 'config_invalid_yaml'
        self.assert_load_success(name)  # no error for some reason

        # invalid json should be ignored
        assert self.plugin_manager.plugins[name]['config'] is None

    def test_get_config_unloaded_plugin(self):
        name = 'nonexistent_plugin'
        with pytest.raises(exceptions.ConfigNotFoundError):
            self.plugin_manager.get_config(name)

    def test_get_config_plugin_without_config(self):
        name = 'valid'
        self.assert_load_success(name)

        with pytest.raises(exceptions.ConfigNotFoundError):
            self.plugin_manager.get_config(name)

    def test_get_config_json(self):
        name = 'config_valid_json'
        self.assert_load_success(name, assert_config_is_none=False)

        self.plugin_manager.get_config(name) == {'test': True}

    def test_get_config_yaml(self):
        name = 'config_valid_yaml'
        self.assert_load_success(name, assert_config_is_none=False)

        self.plugin_manager.get_config(name) == {'test': True}

    def test_plugin_iteration(self):
        plugins = [
            'setup_one_argument',
            'setup_two_arguments',
            'valid',
        ]
        self.assert_load_success(plugins, assert_config_is_none=False)

        for plugin in self.plugin_manager:
            assert plugin == self.plugin_manager.plugins[plugin['name']]

    def test_reload_valid_succeeds(self):
        name = 'valid'
        plugins = [name]

        self.cardinal.reloads = 0

        # first load is not considered a reload
        self.assert_load_success(plugins)
        assert self.cardinal.reloads == 0

        # second load is
        self.assert_load_success(plugins)
        assert self.cardinal.reloads == 1

        # and so on...
        self.assert_load_success(plugins)
        assert self.cardinal.reloads == 2

    def test_reload_exception_in_close_succeeds(self):
        name = 'close_raises_exception'
        plugins = [name]

        self.cardinal.reloads = 0

        self.assert_load_success(plugins)

        # should reload successfully despite bad close()
        self.assert_load_success(plugins)
        assert self.cardinal.reloads == 1

    @pytest.mark.parametrize("plugins", [
        12345,
        0.0,
        object(),
    ])
    def test_unload_plugins_not_a_list_or_string_typeerror(self, plugins):
        with pytest.raises(TypeError):
            self.plugin_manager.unload(plugins)

    def test_unload_plugins_never_loaded_plugin_fails(self):
        name = 'test_never_loaded_plugin'
        plugins = [name]

        assert self.plugin_manager.plugins == {}

        failed_plugins = self.plugin_manager.unload(plugins)

        assert failed_plugins == plugins
        assert self.plugin_manager.plugins == {}

    def test_unload_exception_in_close_fails(self):
        name = 'close_raises_exception'
        plugins = [name]

        self.assert_load_success(plugins)

        failed_plugins = self.plugin_manager.unload(plugins)

        # Failed plugins represents a list of plugins that errored on unload
        # but the plugin should still be removed from the PluginManager.
        #
        # FIXME Unfortunately, this means that a plugin might fail to remove
        # its callbacks from an event, and then be inaccessible by Cardinal.
        assert failed_plugins == plugins
        assert self.plugin_manager.plugins == {}

    @pytest.mark.parametrize("plugins", [
        # This plugin contains no close() method
        'valid',
        ['valid'],  # test list format
        # This plugin has a no-op close() method
        'close_no_arguments',
    ])
    def test_unload_valid_succeeds(self, plugins):
        self.assert_load_success(plugins)

        failed_plugins = self.plugin_manager.unload(plugins)

        assert failed_plugins == []
        assert self.plugin_manager.plugins.keys() == []

    def test_unload_passes_cardinal(self):
        plugin = 'close_one_argument'

        self.assert_load_success(plugin)
        module = self.plugin_manager.plugins[plugin]['module']

        failed_plugins = self.plugin_manager.unload(plugin)

        assert failed_plugins == []
        assert self.plugin_manager.plugins.keys() == []

        # Our close() method will set module.cardinal for us to inspect
        assert module.cardinal is self.cardinal

    def test_unload_too_many_arguments_in_close(self):
        plugin = 'close_too_many_arguments'

        self.assert_load_success(plugin)
        module = self.plugin_manager.plugins[plugin]['module']

        failed_plugins = self.plugin_manager.unload(plugin)

        assert failed_plugins == [plugin]
        assert self.plugin_manager.plugins.keys() == []

        # Our close() method will set module.called to True if called
        assert module.called is False

    def test_unload_all(self):
        self.assert_load_success([
            'valid',
            'close_no_arguments',
            'close_too_many_arguments',
        ])

        assert len(self.plugin_manager.plugins) == 3

        # Doesn't return what failed to unload cleanly, but should unload
        # everything regardless
        self.plugin_manager.unload_all()

        assert self.plugin_manager.plugins == {}

    def test_event_callback_registered(self):
        name = 'event_callback'
        event = 'irc.raw'

        self.assert_load_success(name, assert_callbacks_is_empty=False)
        instance = self.plugin_manager.plugins[name]['instance']

        # test that plugin manager is tracking the callback
        assert len(self.plugin_manager.plugins[name]['callback_ids']) == 1
        assert self.plugin_manager.plugins[name]['callbacks'] == [
            {
                'event_names': [event],
                'method': instance.irc_raw_callback,
            }
        ]

        # test that event manager had callback registered
        self.event_manager.register(event, 1)

        message = 'this is a test message'
        self.event_manager.fire(event, message)

        assert instance.cardinal is self.cardinal
        assert instance.messages == [message]

        self.event_manager.fire(event, message)
        assert instance.messages == [message, message]

    def test_event_callback_unregistered(self):
        name = 'event_callback'
        event = 'irc.raw'

        self.assert_load_success(name, assert_callbacks_is_empty=False)
        instance = self.plugin_manager.plugins[name]['instance']

        # make sure an event is sent to the callback
        self.event_manager.register(event, 1)
        message = 'this is a test message'
        self.event_manager.fire(event, message)
        assert instance.messages == [message]

        # unload and make sure no more events are sent
        self.plugin_manager.unload(name)

        self.event_manager.fire(event, message)
        assert instance.messages == [message]

    def test_load_bad_callback_fails(self):
        name = 'event_callback'
        event = 'irc.raw'

        # this will cause registration to fail, as our callback only takes 1
        # param other than cardinal
        self.event_manager.register(event, 2)

        failed_plugins = self.plugin_manager.load(name)

        assert failed_plugins == [name]
        assert self.plugin_manager.plugins == {}


class TestEventManager(object):
    def setup_method(self):
        mock_cardinal = self.cardinal = Mock(spec=CardinalBot)
        self.event_manager = EventManager(mock_cardinal)

    def _callback(self, cardinal):
        """Used as a test callback."""

    def assert_register_success(self, name, params=0):
        self.event_manager.register(name, params)
        assert name in self.event_manager.registered_events
        assert name in self.event_manager.registered_callbacks
        assert self.event_manager.registered_events[name] == params

    def assert_register_callback_success(self, name, callback=None):
        callback = callback or self._callback

        callback_count = len(self.event_manager.registered_callbacks[name]) \
            if name in self.event_manager.registered_callbacks else 0

        # callback id is used for removal
        callback_id = self.event_manager.register_callback(name, callback)

        assert isinstance(callback_id, basestring)
        assert len(self.event_manager.registered_callbacks[name]) == \
            callback_count + 1

        return callback_id

    def assert_remove_callback_success(self, name, callback_id):
        callback_count = len(self.event_manager.registered_callbacks[name])

        self.event_manager.remove_callback(name, callback_id)

        assert len(self.event_manager.registered_callbacks[name]) == \
            callback_count - 1

    def test_constructor(self):
        assert self.event_manager.cardinal == self.cardinal
        assert isinstance(self.event_manager.logger, logging.Logger)
        assert isinstance(self.event_manager.registered_events, dict)
        assert isinstance(self.event_manager.registered_callbacks, dict)

    def test_register(self):
        name = 'test_event'
        self.assert_register_success(name)
        assert len(self.event_manager.registered_callbacks[name]) == 0

    def test_register_duplicate_event(self):
        name = 'test_event'

        self.assert_register_success(name)

        with pytest.raises(exceptions.EventAlreadyExistsError):
            self.event_manager.register(name, 1)

    @pytest.mark.parametrize("param_count", [
        3.14,
        'foobar',
        object(),
    ])
    def test_register_invalid_param_count(self, param_count):
        with pytest.raises(TypeError):
            self.event_manager.register('test_event', param_count)

    def test_remove(self):
        name = 'test_event'
        self.assert_register_success(name)

        self.event_manager.remove(name)

        assert name not in self.event_manager.registered_events
        assert name not in self.event_manager.registered_callbacks

    def test_remove_event_doesnt_exist(self):
        name = 'test_event'

        with pytest.raises(exceptions.EventDoesNotExistError):
            self.event_manager.remove(name)

    def test_add_callback(self):
        def callback(cardinal):
            pass

        name = 'test_event'
        self.assert_register_success(name)

        self.assert_register_callback_success(name, callback)

    def test_add_callback_non_callable(self):
        callback = 'this is not callable'

        name = 'test_event'
        self.assert_register_success(name)

        with pytest.raises(exceptions.EventCallbackError):
            self.event_manager.register_callback(name, callback)

    def test_add_callback_without_registered_event(self):
        # only accepts cardinal
        def callback(cardinal):
            pass

        # accepts cardinal and another param
        def callback2(cardinal, _):
            pass

        name = 'test_event'

        # should not validate params aside from at least accepting cardinal
        self.assert_register_callback_success(name, callback)
        self.assert_register_callback_success(name, callback2)

    def test_add_callback_method_ignores_self(self):
        name = 'test_event'

        self.assert_register_success(name)
        self.assert_register_callback_success(name, self._callback)

    def test_add_callback_validates_required_args(self):
        def callback(cardinal, one_too_many_args):
            pass

        name = 'test_event'

        self.assert_register_success(name)
        with pytest.raises(exceptions.EventCallbackError):
            self.event_manager.register_callback(name, callback)

    def test_add_callback_requires_cardinal_arg(self):
        def callback():
            pass

        name = 'test_event'

        with pytest.raises(exceptions.EventCallbackError):
            self.event_manager.register_callback(name, callback)

    def test_remove_callback(self):
        name = 'test_event'

        cb_id = self.assert_register_callback_success(name)
        self.assert_remove_callback_success(name, cb_id)

    def test_remove_callback_nonexistent_event_silent(self):
        name = 'test_event'
        callback_id = 'nonexistent'

        assert name not in self.event_manager.registered_callbacks
        self.event_manager.remove_callback(name, callback_id)

    def test_remove_callback_nonexistent_callback_silent(self):
        name = 'test_event'
        callback_id = 'nonexistent'

        self.assert_register_success(name)

        assert len(self.event_manager.registered_callbacks[name]) == 0
        self.event_manager.remove_callback(name, callback_id)
        assert len(self.event_manager.registered_callbacks[name]) == 0

    def test_fire_event_does_not_exist(self):
        name = 'test_event'

        with pytest.raises(exceptions.EventDoesNotExistError):
            self.event_manager.fire(name)

    @defer.inlineCallbacks
    def test_fire(self):
        args = []

        def callback(*fargs):
            for arg in fargs:
                args.append(arg)

        name = 'test_event'

        self.assert_register_success(name)
        self.assert_register_callback_success(name, callback)

        accepted = yield self.event_manager.fire(name)

        assert accepted is True
        assert args == [self.cardinal]

    @defer.inlineCallbacks
    def test_fire_callback_rejects(self):
        args = []

        def callback(*fargs):
            for arg in fargs:
                args.append(arg)
            raise exceptions.EventRejectedMessage()

        name = 'test_event'

        self.assert_register_success(name)
        self.assert_register_callback_success(name, callback)

        accepted = yield self.event_manager.fire(name)

        assert accepted is False
        assert args == [self.cardinal]

    @defer.inlineCallbacks
    def test_fire_multiple_callbacks(self):
        args = []

        def generate_cb(reject):
            def callback(*fargs):
                for arg in fargs:
                    args.append(arg)
                if reject:
                    raise exceptions.EventRejectedMessage()
            return callback

        name = 'test_event'

        self.assert_register_success(name)
        self.assert_register_callback_success(name, generate_cb(True))
        self.assert_register_callback_success(name, generate_cb(False))
        self.assert_register_callback_success(name, generate_cb(False))

        accepted = yield self.event_manager.fire(name)

        assert accepted is True
        assert args == [self.cardinal, self.cardinal, self.cardinal]

    @defer.inlineCallbacks
    def test_fire_multiple_callbacks_all_reject(self):
        def generate_cb(reject):
            def callback(*fargs):
                if reject:
                    raise exceptions.EventRejectedMessage()
            return callback

        name = 'test_event'

        self.assert_register_success(name)
        self.assert_register_callback_success(name, generate_cb(True))
        self.assert_register_callback_success(name, generate_cb(True))

        accepted = yield self.event_manager.fire(name)

        assert accepted is False

    @defer.inlineCallbacks
    def test_fire_multiple_callbacks_one_errors(self):
        def generate_cb(error):
            def callback(*fargs):
                if error:
                    raise Exception()
            return callback

        name = 'test_event'

        self.assert_register_success(name)
        self.assert_register_callback_success(name, generate_cb(False))
        self.assert_register_callback_success(name, generate_cb(True))

        accepted = yield self.event_manager.fire(name)

        assert accepted is True

    @defer.inlineCallbacks
    def test_fire_multiple_callbacks_all_error(self):
        def generate_cb(error):
            def callback(*fargs):
                if error:
                    raise Exception()
            return callback

        name = 'test_event'

        self.assert_register_success(name)
        self.assert_register_callback_success(name, generate_cb(True))
        self.assert_register_callback_success(name, generate_cb(True))
        self.assert_register_callback_success(name, generate_cb(True))

        accepted = yield self.event_manager.fire(name)

        assert accepted is False

    def test_add_callback_wont_duplicate_id(self):
        name = 'test_event'

        with patch.object(self.event_manager, '_generate_id') as mock_gen_id:
            mock_gen_id.side_effect = ['ABC123', 'ABC123', 'DEF456']
            event_id1 = self.assert_register_callback_success(name)
            event_id2 = self.assert_register_callback_success(name)

        assert event_id1 == 'ABC123'
        assert event_id2 != 'ABC123'
