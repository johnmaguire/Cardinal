#!/usr/bin/env python

from past.builtins import basestring
import os
import sys
import argparse
import logging
import logging.config

from twisted.internet import reactor

from cardinal.config import ConfigParser, ConfigSpec
from cardinal.bot import CardinalBotFactory


def setup_logging(config=None):
    if config is None:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        logging.config.dictConfig(config)

    return logging.getLogger(__name__)


if __name__ == "__main__":
    # Create a new instance of ArgumentParser with a description about Cardinal
    arg_parser = argparse.ArgumentParser(description="""
Cardinal IRC bot

A Twisted IRC bot designed to be simple to use and and easy to extend.

https://github.com/JohnMaguire/Cardinal
""", formatter_class=argparse.RawDescriptionHelpFormatter)

    arg_parser.add_argument('config', metavar='config',
                            help='custom config location')

    # Parse command-line arguments
    args = arg_parser.parse_args()
    config_file = args.config

    # Define the config spec and create a parser for our internal config
    spec = ConfigSpec()
    spec.add_option('nickname', basestring, 'Cardinal')
    spec.add_option('password', basestring, None)
    spec.add_option('username', basestring, None)
    spec.add_option('realname', basestring, None)
    spec.add_option('network', basestring, 'irc.freenode.net')
    spec.add_option('port', int, 6667)
    spec.add_option('server_password', basestring, None)
    spec.add_option('server_commands', list, [])
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
        'urbandict',
        'seen'
    ])
    spec.add_option('blacklist', dict, {})
    spec.add_option('logging', dict, None)

    parser = ConfigParser(spec)

    # Load config file
    try:
        config = parser.load_config(config_file)
    except Exception:
        # Need to setup a logger early
        logger = setup_logging()
        logger.exception("Unable to load config: {}".format(config_file))
        sys.exit(1)

    # Config loaded, setup the logger
    logger = setup_logging(config['logging'])

    logger.info("Config loaded: {}".format(config_file))

    # Determine storage directory
    if config['storage'] is not None:
        if config['storage'].startswith('/'):
            config['storage'] = config['storage']
        else:
            config['storage'] = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                config['storage']
            )

        logger.info("Storage path: {}".format(config['storage']))

        directories = [
            os.path.join(config['storage'], 'database'),
            os.path.join(config['storage'], 'logs'),
        ]

        for directory in directories:
            if not os.path.exists(directory):
                logger.info(
                    "Initializing storage directory: {}".format(directory))
                os.makedirs(directory)

    # If no username is supplied, default to nickname
    if config['username'] is None:
        config['username'] = config['nickname']

    # Instance a new factory, and connect with/without SSL
    logger.debug("Instantiating CardinalBotFactory")
    factory = CardinalBotFactory(config['network'],
                                 config['server_password'],
                                 config['server_commands'],
                                 config['channels'],
                                 config['nickname'],
                                 config['password'],
                                 config['username'],
                                 config['realname'],
                                 config['plugins'],
                                 config['blacklist'],
                                 config['storage'])

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
