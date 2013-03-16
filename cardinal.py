#!/usr/bin/env python

# Copyright (c) 2013 John Maguire <john@leftforliving.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy 
# of this software and associated documentation files (the "Software"), to 
# deal in the Software without restriction, including without limitation the 
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or 
# sell copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS 
# IN THE SOFTWARE.

import argparse
from getpass import getpass

from twisted.internet import reactor
from CardinalBot import CardinalBotFactory

DEFAULT_NICKNAME = 'Cardinal'
DEFAULT_PASSWORD = None
DEFAULT_NETWORK = 'irc.darchoods.net'
DEFAULT_PORT = 6667
DEFAULT_CHANNELS = ('#bots',)
DEFAULT_PLUGINS = (
    'ping',
    'urls',
    'weather',
#    'admin',
#    'lastfm',
)
DEFAULT_SSL = False

parser = argparse.ArgumentParser(description="""
Cardinal IRC bot

A Python/Twisted-powered modular IRC bot. Aimed to be simple to use, simple
to develop. For information on developing plugins, visit the project page
below.

https://github.com/JohnMaguire2013/Cardinal
""", formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('-n', '--nickname', default=DEFAULT_NICKNAME,
                    metavar='nickname', help='nickname to connect as')
parser.add_argument('--password', default=DEFAULT_PASSWORD, action='store_true',
                    help='set this flag to get a password prompt for identifying')

parser.add_argument('-i', '--network', default=DEFAULT_NETWORK,
                    metavar='network', help='network to connect to')
parser.add_argument('-o', '--port', default=DEFAULT_PORT, type=int,
                    metavar='port', help='network port to connect to')

parser.add_argument('-c', '--channels', default=DEFAULT_CHANNELS, nargs='*',
                    metavar='channel', help='list of channels to connect to on startup')
parser.add_argument('-p', '--plugins', default=DEFAULT_PLUGINS, nargs='*',
                    metavar='plugin', help='list of plugins to load on startup')

parser.add_argument('-s', '--ssl', default=DEFAULT_SSL, action='store_true',
                    help='you must set this flag for SSL connections')

if __name__ == "__main__":
    args = parser.parse_args()
    if args.password:
        password = getpass('NickServ password: ')
    else:
        password = DEFAULT_PASSWORD
    factory = CardinalBotFactory(args.network, args.channels, args.nickname, password, args.plugins)

    if not args.ssl:
        reactor.connectTCP(args.network, args.port, factory)
    else:
        from twisted.internet import ssl
        reactor.connectSSL(args.network, args.port, factory, ssl.ClientContextFactory())
    reactor.run()
