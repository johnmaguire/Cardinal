# Meet Cardinal.

[![Build Status](https://travis-ci.org/JohnMaguire/Cardinal.svg?branch=master)](https://travis-ci.org/JohnMaguire/Cardinal) [![Coverage Status](https://coveralls.io/repos/JohnMaguire/Cardinal/badge.svg?branch=master&service=github)](https://coveralls.io/github/JohnMaguire/Cardinal?branch=master)

Python Twisted IRC bot with a focus on ease of development.

You can find us at #cardinal on the [DarkScience](http://www.darkscience.net/) IRC network (irc.darkscience.net/+6697 &mdash; SSL required)

## What can Cardinal do?

Anything, if you're creative! But Cardinal does come with some plugins to get you started...

* Fetching URL titles
* Google searches
* Weather report
* Now playing w/ Last.fm
* Reminders
* Urban Dictionary definitions
* Wikipedia definitions
* ... and more!

And Cardinal is still in development! But what makes Cardinaly truly special is the ease of adding new functionality.

## Basic Usage

### Configuration

Copy the `config/config.example.json` (virtualenv) or `config/config.docker.json` (Docker) file to `config/config.json` (or, if you are using Cardinal on multiple networks, something like `config.freenode.json`) and modify it to suit your needs.

You should also add your nick and vhost to the `plugins/admin/config.json` file in the format `nick@vhost` in order to take advantage of admin-only commands.

### Installation & Running

You can run Cardinal as a Docker container, or install Cardinal inside of a [Python virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

#### Docker

First, install [Docker](https://docs.docker.com/install/) and [docker-compose](https://docs.docker.com/compose/install/).

After configuring Cardinal (see above), simply run `docker-compose up -d` if you are storing your config as `config/config.json`. Otherwise, you will need to create a `docker-compose.override.yml` file like so:

```yaml
version: "2.1"
services:
    cardinal:
        command: config/my_config_file.json
```

#### virtualenv

`virtualenv -p /usr/bin/python2.7 . && source bin/activate`

Make sure you have Python 2.7 installed, and run `pip install -r requirements.txt` to install all Python dependencies.

**Note:** Make sure you have `libssl-dev` and `libffi-dev` installed on Debian (or the equivelant package for your distro) or installation of some dependencies may not work correctly.

After installation, simply type `./cardinal.py config/config.json` (change `config/config.json` to your config location).

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

Pull requests and bug reports accepted. If you're submitting a pull request, you may add your name to the CONTRIBUTORS file with a separate commit in the same branch as your modification.

Cardinal is a public, open-source project, licensed under the MIT License. Anyone may contribute.
