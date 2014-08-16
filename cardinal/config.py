import logging
import json
import argparse

# Hardcoded defaults in case the config file is missing and no command-line
# options are specified
DEFAULT_NICKNAME = 'Cardinal'
DEFAULT_PASSWORD = None
DEFAULT_NETWORK = 'irc.freenode.net'
DEFAULT_PORT = 6667
DEFAULT_SSL = False
DEFAULT_CHANNELS = ('#bots',)
DEFAULT_PLUGINS = (
    'help',
    'admin',
    'ping',
    'urls',
    'notes',
    'calculator',
    'weather',
    'remind',
    'lastfm',
    'youtube',
    'join_on_invite',
#    'event_examples',
)

class ConfigParser(object):
    """A class to make parsing of JSON configs easier.

    This class adds support for both the internal Cardinal config as well as
    config files for plugins. It helps to combine hard-coded defaults with
    values provided by a user (either through a JSON-encoded config file or
    command-line input.)

    """
    config = {}

    def _option_is_valid(self, config, option, type):
        """Returns whether an option exists in the config and the correct type

        Keyword arguments:
          config -- A JSON-decoded object containing a config
          option -- The name of an option to validate
          type   -- A Python object to check if option matches the type of

        Returns:
          bool -- True if validation succeeds, false if not

        """
        if option in config and isinstance(config[option], type):
            return True

        return False

    def _convert_json(self, json_object, called_by_self=False):
        """Converts json.load() or json.loads() return to UTF-8.

        By default, json.load() will return an object with unicode strings.
        Unfortunately, these cause problems with libraries like Twisted, so we
        need to convert them into UTF-8 encoded strings.

        Keyword arguments:
          json_object    -- Dict object returned by json.load() / json.loads().
          called_by_self -- Internal parameter only used for sanity check.

        Return:
          dict -- A UTF-8 encoded version of json_object.

        """
        if not called_by_self and not isinstance(json_object, dict):
            raise ValueError("Object must be a dict")

        if isinstance(json_object, dict):
            return {
                self._convert_json(key, True): self._convert_json(value, True) for key, value in json_object.iteritems()
            }
        elif isinstance(json_object, list):
            return [
                self._convert_json(element, True) for element in json_object
            ]
        elif isinstance(json_object, unicode):
            return json_object.encode('utf-8')
        else:
            return json_object

    def load_config(self, file):
        """Attempts to load a JSON config file for Cardinal.

        Takes a file path, attempts to decode its contents from JSON, then
        validate known config options to see if they can safely be loaded in.
        If they can't, the default option (DEFAULT_* constants) are used in
        their place. The final merged dictionary object is saved to the
        instance and returned.

        Keyword arguments:
          file -- Path to a JSON config file.

        Return:
          dict -- Dictionary object of the entire config.

        """
        # Attempt to load and parse the config file
        try:
            f = open(file, 'r')
            config = self._convert_json(json.load(f))
            f.close()
        # File did not exist or we can't open it for another reason
        except IOError:
            logging.warning(
                "Can't open %s (using defaults / command-line values)" % file
            )
        # Thrown by json.load() when the content isn't valid JSON
        except ValueError:
            logging.warning(
                "Invalid JSON in %s, (using defaults / command-line values" % file
            )
        else:
            # File was loaded successfully, now we validate all the options and set
            # the corresponding constant if they appear to be valid
            if not self._option_is_valid(config, 'nickname', basestring):
                config['nickname'] = DEFAULT_NICKNAME
            if not self._option_is_valid(config, 'password', basestring):
                config['password'] = DEFAULT_PASSWORD
            if not self._option_is_valid(config, 'network', basestring):
                config['network']  = DEFAULT_NETWORK
            if not self._option_is_valid(config, 'port', int):
                config['port']     = DEFAULT_PORT
            if not self._option_is_valid(config, 'ssl', bool):
                config['ssl']      = DEFAULT_SSL
            if not self._option_is_valid(config, 'channels', list):
                config['channels'] = DEFAULT_CHANNELS
            if not self._option_is_valid(config, 'plugins', list):
                config['plugins']  = DEFAULT_PLUGINS

        self.config = config
        return config

    def generate_argparser(self):
        """Generates the help file and command-line option parser.

        Keyword arguments:
          config -- A config dictionary from load_config() for default values

        Return:
          object -- A built ArgumentParser object

        """
        parser = argparse.ArgumentParser(description="""
    Cardinal IRC bot

    A Python/Twisted-powered modular IRC bot. Aimed to be simple to use, simple
    to develop. For information on developing plugins, visit the project page
    below.

    https://github.com/JohnMaguire/Cardinal
        """, formatter_class=argparse.RawDescriptionHelpFormatter)

        parser.add_argument('-n', '--nickname', default=self.config['nickname'],
                            metavar='nickname', help='nickname to connect as')
        parser.add_argument('--password', default=None, action='store_true',
                            help='set this flag to get a password prompt for identifying')
        parser.add_argument('-i', '--network', default=self.config['network'],
                            metavar='network', help='network to connect to')
        parser.add_argument('-o', '--port', default=self.config['port'], type=int,
                            metavar='port', help='network port to connect to')
        parser.add_argument('-s', '--ssl', default=self.config['ssl'], action='store_true',
                            help='you must set this flag for SSL connections')
        parser.add_argument('-c', '--channels', default=self.config['channels'], nargs='*',
                            metavar='channel', help='list of channels to connect to on startup')
        parser.add_argument('-p', '--plugins', default=self.config['plugins'], nargs='*',
                            metavar='plugin', help='list of plugins to load on startup')

        return parser

