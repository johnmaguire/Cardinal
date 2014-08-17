#!/usr/bin/env python

import os
import logging
import json
import argparse
from getpass import getpass

from twisted.internet import reactor
from cardinal.config import ConfigParser, ConfigSpec
from cardinal.bot import CardinalBotFactory

# If this file is being run directly, set the logging level, load config file,
# parse command-line arguments, and instance and run CardinalBot
if __name__ == "__main__":
    # Set logging to info by default
    logging.basicConfig(level=logging.INFO)

    # Define the ArgumentParser for CLI options
    arg_parser = argparse.ArgumentParser(description="""
Cardinal IRC bot

A Python/Twisted-powered modular IRC bot. Aimed to be simple to use, simple
to develop. For information on developing plugins, visit the project page
below.

https://github.com/JohnMaguire/Cardinal
""", formatter_class=argparse.RawDescriptionHelpFormatter)

    arg_parser.add_argument('-n', '--nickname', metavar='nickname', help='nickname to connect as')
    arg_parser.add_argument('--password', action='store_true', help='set this flag to get a password prompt for identifying')
    arg_parser.add_argument('-i', '--network', metavar='network', help='network to connect to')
    arg_parser.add_argument('-o', '--port', type=int, metavar='port', help='network port to connect to')
    arg_parser.add_argument('-s', '--ssl', action='store_true', help='you must set this flag for SSL connections')
    arg_parser.add_argument('-c', '--channels', nargs='*', metavar='channel', help='list of channels to connect to on startup')
    arg_parser.add_argument('-p', '--plugins', nargs='*', metavar='plugin', help='list of plugins to load on startup')

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
        'youtube'
    ])
    parser = ConfigParser(spec)

    # First attempt to load config.json for config options
    logging.info("Looking for and attempting to load config.json")
    parser.load_config('config.json')

    # Parse command-line arguments last, as they should override both project
    # defaults and the user config (if available)
    logging.info("Parsing command-line arguments")
    args = arg_parser.parse_args()

    # If SSL is set to false, set it to None (small hack - action 'store_true'
    # in arg_parse defaults to False. False instead of None will overwrite our
    # config settings.)
    if not args.ssl:
        args.ssl = True

    # If the password flag was set, let the user safely type in their password
    if args.password:
        args.password = getpass('NickServ password: ')
    else:
        args.password = None

    # Merge the args into the config object
    logging.info("Merging command-line arguments into config")
    config = parser.merge_argparse_args_into_config(args)

    # Instance a new factory, and connect with/without SSL
    logging.info("Initializing Cardinal factory")
    factory = CardinalBotFactory(config['network'], config['channels'],
        config['nickname'], config['password'], config['plugins'])

    if not config['ssl']:
        logging.info(
            "Connecting over plaintext to %s:%d" % (config['network'], config['port'])
        )
        reactor.connectTCP(config['network'], config['port'], factory)
    else:
        logging.info(
            "Connecting over SSL to %s:%d" % (config['network'], config['port'])
        )
        from twisted.internet import ssl
        reactor.connectSSL(config['network'], config['port'], factory, ssl.ClientContextFactory())

    # Run the Twisted reactor
    reactor.run()
