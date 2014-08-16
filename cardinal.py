#!/usr/bin/env python

import os
import logging
import json
import argparse
from getpass import getpass

from twisted.internet import reactor
from CardinalBot import CardinalBotFactory

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

def valid_option(config, option, type):
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

def load_config(file):
    """Attempts to load a JSON config file for Cardinal.

    Takes a file path, attempts to decode its contents from JSON, then validate
    known config options to see if they can safely be loaded in. If they can't,
    the default option (DEFAULT_* constants) are used in their place. The final
    merged dictionary object is returned.

    Keyword arguments:
      file -- Path to a JSON config file.

    Return:
      dict -- Dictionary object of the entire config.

    """
    # Attempt to load and parse the config file
    try:
        f = open(file, 'r')
        config = json.load(f)
        f.close()
    except IOError:
        logging.warning("Can't open %s, using project defaults / command-line values" % file)
    except ValueError:
        logging.warning("Invalid JSON in %s, using project defaults / command-line values" % file)
    else:
        # File was loaded successfully, now we validate all the options and set
        # the corresponding constant if they appear to be valid
        if not valid_option(config, 'nickname', basestring):
            config['nickname'] = DEFAULT_NICKNAME
        if not valid_option(config, 'password', basestring):
            config['password'] = DEFAULT_PASSWORD
        if not valid_option(config, 'network', basestring):
            config['network']  = DEFAULT_NETWORK
        if not valid_option(config, 'port', int):
            config['port']     = DEFAULT_PORT
        if not valid_option(config, 'ssl', bool):
            config['ssl']      = DEFAULT_SSL
        if not valid_option(config, 'channels', list):
            config['channels'] = DEFAULT_CHANNELS
        if not valid_option(config, 'plugins', list):
            config['plugins']  = DEFAULT_PLUGINS

    return config

def generate_parser(config):
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

    parser.add_argument('-n', '--nickname', default=config['nickname'],
                        metavar='nickname', help='nickname to connect as')
    parser.add_argument('--password', default=None, action='store_true',
                        help='set this flag to get a password prompt for identifying')
    parser.add_argument('-i', '--network', default=config['network'],
                        metavar='network', help='network to connect to')
    parser.add_argument('-o', '--port', default=config['port'], type=int,
                        metavar='port', help='network port to connect to')
    parser.add_argument('-s', '--ssl', default=config['ssl'], action='store_true',
                        help='you must set this flag for SSL connections')
    parser.add_argument('-c', '--channels', default=config['channels'], nargs='*',
                        metavar='channel', help='list of channels to connect to on startup')
    parser.add_argument('-p', '--plugins', default=config['plugins'], nargs='*',
                        metavar='plugin', help='list of plugins to load on startup')

    return parser

# If this file is being run directly, set the logging level, load config file,
# parse command-line arguments, and instance and run CardinalBot
if __name__ == "__main__":
    # Set logging to info by default
    logging.basicConfig(level=logging.INFO)

    # First attempt to load config.json for config options
    logging.info("Looking for and attempting to load config.json")
    config = load_config('config.json')

    # Parse command-line arguments last, as they should override both project
    # defaults and the user config (if available)
    logging.info("Parsing command-line arguments")
    parser = generate_parser(config)
    args   = parser.parse_args()

    # If the password flag was set, let the user safely type in their password
    if args.password:
        password = getpass('NickServ password: ')
    else:
        password = config['password']

    # Instance a new factory, and connect with/without SSL
    factory = CardinalBotFactory(args.network, args.channels, args.nickname, password, args.plugins)
    if not args.ssl:
        reactor.connectTCP(args.network, args.port, factory)
    else:
        from twisted.internet import ssl
        reactor.connectSSL(args.network, args.port, factory, ssl.ClientContextFactory())

    # Run the Twisted reactor
    reactor.run()
