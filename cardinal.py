#!/usr/bin/env python

import os
import sys
import argparse
import logging
import logging.config
from getpass import getpass

from twisted.internet import reactor

from cardinal.config import ConfigParser, ConfigSpec
from cardinal.bot import CardinalBotFactory

if __name__ == "__main__":

    # Create a new instance of ArgumentParser with a description about Cardinal
    arg_parser = argparse.ArgumentParser(description="""
Cardinal IRC bot

A Python/Twisted-powered modular IRC bot. Aimed to be simple to use, simple
to develop. For information on developing plugins, visit the project page
below.

https://github.com/JohnMaguire/Cardinal
""", formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add all the possible arguments
    arg_parser.add_argument('-n', '--nickname', metavar='nickname',
                            help='nickname to connect as')

    arg_parser.add_argument('--password', action='store_true',
                            help='set this flag to get a password prompt for '
                                 'identifying')

    arg_parser.add_argument('-u', '--username', metavar='username',
                            help='username (ident) of the bot')

    arg_parser.add_argument('-r', '--realname', metavar='realname',
                            help='Real name of the bot')

    arg_parser.add_argument('-i', '--network', metavar='network',
                            help='network to connect to')

    arg_parser.add_argument('-o', '--port', type=int, metavar='port',
                            help='network port to connect to')

    arg_parser.add_argument('-P', '--spassword', metavar='server_password',
                            help='password to connect to the network with')

    arg_parser.add_argument('-s', '--ssl', action='store_true',
                            help='you must set this flag for SSL connections')

    arg_parser.add_argument('-c', '--channels', nargs='*', metavar='channel',
                            help='list of channels to connect to on startup')

    arg_parser.add_argument('-p', '--plugins', nargs='*', metavar='plugin',
                            help='list of plugins to load on startup')

    arg_parser.add_argument('--config', metavar='config',
                            help='custom config location')

    # Define the config spec and create a parser for our internal config
    spec = ConfigSpec()
    spec.add_option('nickname', basestring, 'Cardinal')
    spec.add_option('password', basestring, None)
    spec.add_option('username', basestring, None)
    spec.add_option('realname', basestring, None)
    spec.add_option('network', basestring, 'irc.freenode.net')
    spec.add_option('port', int, 6667)
    spec.add_option('server_password', basestring, None)
    spec.add_option('ssl', bool, False)
    spec.add_option('storage', basestring, os.path.join(
        os.path.dirname(os.path.realpath(sys.argv[0])),
        'storage'
    ))
    spec.add_option('channels', list, ['#bots'])
    spec.add_option('plugins', list, [
        'wikipedia',
        'ping',
        'help',
        'admin',
        'join_on_invite',
        'urls',
        'calculator',
        'lastfm',
        'remind',
        'weather',
        'youtube',
        'urbandict'
    ])
    spec.add_option('logging', dict, None)

    parser = ConfigParser(spec)

    # Parse command-line arguments
    args = arg_parser.parse_args()

    # Attempt to load config.json for config options
    config_file = args.config
    if config_file is None:
        config_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'config.json'
        )

    # Load config file
    parser.load_config(config_file)

    # If SSL is set to false, set it to None (small hack - action 'store_true'
    # in arg_parse defaults to False. False instead of None will overwrite our
    # config settings.)
    if not args.ssl:
        args.ssl = None

    # If the password flag was set, let the user safely type in their password
    if args.password:
        args.password = getpass('NickServ password: ')
    else:
        args.password = None

    # Merge the args into the config object
    config = parser.merge_argparse_args_into_config(args)

    # If user defined logging config, use it, otherwise use default
    if config['logging'] is not None:
        logging.config.dictConfig(config['logging'])
    else:
        # Set default log level to INFO and get some pretty formatting
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # Get a logger!
    logger = logging.getLogger(__name__)

    # Set the storage directory
    storage_path = None
    if config['storage'] is not None:
        if config['storage'].startswith('/'):
            storage_path = config['storage']
        else:
            storage_path = os.path.join(
                os.path.dirname(os.path.realpath(sys.argv[0])),
                config['storage']
            )

        logger.info("Storage path set to %s" % storage_path)

        directories = [
            os.path.join(storage_path, 'database'),
            os.path.join(storage_path, 'logs'),
        ]

        for directory in directories:
            if not os.path.exists(directory):
                logger.info(
                    "Storage directory %s does not exist, creating it..",
                    directory)

                os.makedirs(directory)

    """If no username is supplied, set it to the nickname. """
    if config['username'] is None:
        config['username'] = config['nickname']

    # Instance a new factory, and connect with/without SSL
    logger.debug("Instantiating CardinalBotFactory")
    factory = CardinalBotFactory(config['network'], config['server_password'],
                                 config['channels'],
                                 config['nickname'], config['password'],
                                 config['username'],
                                 config['realname'],
                                 config['plugins'],
                                 storage_path)

    if not config['ssl']:
        logger.info(
            "Connecting over plaintext to %s:%d" %
            (config['network'], config['port'])
        )

        reactor.connectTCP(config['network'], config['port'], factory)
    else:
        logger.info(
            "Connecting over SSL to %s:%d" %
            (config['network'], config['port'])
        )

        # For SSL, we need to import the SSL module from Twisted
        from twisted.internet import ssl
        reactor.connectSSL(config['network'], config['port'], factory,
                           ssl.ClientContextFactory())

    # Run the Twisted reactor
    reactor.run()
