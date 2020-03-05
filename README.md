# Meet Cardinal.

[![Build Status](https://travis-ci.org/JohnMaguire/Cardinal.svg?branch=master)](https://travis-ci.org/JohnMaguire/Cardinal) [![Coverage Status](https://coveralls.io/repos/JohnMaguire/Cardinal/badge.svg?branch=master&service=github)](https://coveralls.io/github/JohnMaguire/Cardinal?branch=master)

Python Twisted IRC bot with a focus on ease of development.

You can find us at #cardinal on the [DarkScience](http://www.darkscience.net/) IRC network (irc.darkscience.net/+6697 &mdash; SSL required)

## What can Cardinal do?

Anything, if you're creative! But Cardinal does come with some plugins to get you started...

* Fetching URL titles
* sed-like substitutions
* Reminders
* Weather reports
* Google searches
* Now playing w/ Last.fm
* Urban Dictionary definitions
* Wikipedia definitions
* Stock ticker
* ... and more!

And Cardinal is still in development! But what makes Cardinaly truly special is the ease of adding new functionality.

## Basic Usage

### Configuration

Copy the `config.example.json` file to `config/config.json` (you can use another filename as well, such as `config.freenode.json` if you plan to run Cardinal on multiple networks).

At bare minimum, you should also add your nick and vhost to the `plugins/admin/config.json` file in the format `nick@vhost` in order to take advantage of admin-only commands (such as reloading plugins, telling Cardinal to join a channel, or blacklisting plugins within a channel).

### Running

Cardinal is run via a Docker container. To get started, install [Docker](https://docs.docker.com/install/) and [docker-compose](https://docs.docker.com/compose/install/).

After configuring Cardinal (see above), simply run `docker-compose up -d` if you are storing your config as `config/config.json`. Otherwise, you will need to create a `docker-compose.override.yml` file like so:

```yaml
version: "2.1"
services:
    cardinal:
        command: config/my_config_file.json
```

## Writing Plugins

Cardinal was designed with ease of development in mind.

```python
from cardinal.decorators import command, help

class HelloWorldPlugin(object):
    @command(['hello', 'hi'])
    @help("Responds to the user with a greeting.")
    @help("Syntax: .hello")
    def hello(self, cardinal, user, channel, msg):
        nick, ident, vhost = user
        cardinal.sendMsg(channel, "Hello {}!".format(nick))

def setup():
    return HelloWorldPlugin()
```

[Visit the wiki](https://github.com/JohnMaguire/Cardinal/wiki/Writing-Plugins) for detailed instructions.

## Contributing

Cardinal is a public, open-source project, licensed under the MIT License. Anyone may contribute.

If you're submitting a pull request, you may add your name to the CONTRIBUTORS file with a separate commit in the same branch as your modification.
