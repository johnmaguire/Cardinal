#!/usr/bin/env python

import logging
import argparse
from getpass import getpass

from twisted.internet import reactor

from cardinal.config import ConfigParser, ConfigSpec
from cardinal.bot import CardinalBotFactory

if __name__ == "__main__":
    # Set default log level to INFO and get some pretty formatting
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)

    # Create a new instance of ArgumentParser with a description about Cardinal
    arg_parser = argparse.ArgumentParser(description="""
Cardinal IRC bot

A Python/Twisted-powered modular IRC bot. Aimed to be simple to use, simple
to develop. For information on developing plugins, visit the project page
below.

https://github.com/JohnMaguire/Cardinal
""", formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add all the possible arguments
    #
    # TODO: Shorten this? Maybe some of these are unnecessary.
    # TODO: Add option for a config file location.
    arg_parser.add_argument('-n', '--nickname', metavar='nickname',
        help='nickname to connect as')
    arg_parser.add_argument('--password', action='store_true',
        help='set this flag to get a password prompt for identifying')
    arg_parser.add_argument('-i', '--network', metavar='network',
        help='network to connect to')
    arg_parser.add_argument('-o', '--port', type=int, metavar='port',
        help='network port to connect to')
    arg_parser.add_argument('-s', '--ssl', action='store_true',
        help='you must set this flag for SSL connections')
    arg_parser.add_argument('-c', '--channels', nargs='*', metavar='channel',
        help='list of channels to connect to on startup')
    arg_parser.add_argument('-p', '--plugins', nargs='*', metavar='plugin',
        help='list of plugins to load on startup')

    # Define the config spec and create a parser for our internal config
    spec = ConfigSpec()
    spec.add_option('nickname', basestring, 'Cardinal')
    spec.add_option('password', basestring, None)
    spec.add_option('network', basestring, 'irc.freenode.net')
    spec.add_option('port', int, 6667)
    spec.add_option('ssl', bool, False)
    spec.add_option('channels', list, ['#bots'])
    spec.add_option('plugins', list, [
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

    # TODO: Write a get_parser() method for ConfigSpec that handles instancing
    # and keeping track of the instance.
    parser = ConfigParser(spec)

    # First attempt to load config.json for config options
    #
    # TODO: Make sure that we're looking for config.json in the user's current
    # working directory, rather than relative to this file.
    logger.debug("Attempting to load config.json if it existss")
    parser.load_config('config.json')

    # Parse command-line arguments last, as they should override both project
    # defaults and the user config (if available)
    logger.debug("Parsing command-line arguments")
    args = arg_parser.parse_args()

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
    logger.debug("Merging command-line arguments into config")
    config = parser.merge_argparse_args_into_config(args)

    # Instance a new factory, and connect with/without SSL
    logger.debug("Instantiating CardinalBotFactory")
    factory = CardinalBotFactory(config['network'], config['channels'],
        config['nickname'], config['password'], config['plugins'])

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
