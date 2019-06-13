# Meet Cardinal.

[![Build Status](https://travis-ci.org/JohnMaguire/Cardinal.svg?branch=master)](https://travis-ci.org/JohnMaguire/Cardinal) [![Coverage Status](https://coveralls.io/repos/JohnMaguire/Cardinal/badge.svg?branch=master&service=github)](https://coveralls.io/github/JohnMaguire/Cardinal?branch=master)

Another IRC bot, you say? Just what the world needed!

Cardinal is a modular, Twisted-based IRC bot written in Python. Batteries included!

Cardinal's goal is to make plugin development easy and powerful, and to fill in the gaps where other Python IRC bots fall short.

You can join us at #cardinal on the [DarkScience](http://www.darkscience.net/) IRC network (irc.darkscience.net/+6697 &mdash; SSL required)

## What can Cardinal do?

Anything, as long as you're creative enough! But Cardinal does come with some plugins to get you started...

* Fetching URL information (custom parsers for Github, YouTube, and Wikipedia)
* On-the-fly Googling
* Weather lookup
* Last.fm integration
* Reminders
* Calculator & unit conversion
* Notes (use Cardinal as an info bot)
* Urban Dictionary definitions
* Admin control (hot load plugins, inspect running code, etc.)
* ... and more!

Plus, Cardinal is still in active development! Features are being added as quickly as they can be thought up and coded. But Cardinal's killer feature is the ease of writing new plugins.

## Basic Usage

### Installation

It is recommended that you install and use Cardinal inside of a [Python virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/). You can do so by running the following command inside of your cloned repository.

`virtualenv -p /usr/bin/python2.7 . && source bin/activate`

Make sure you have Python 2.7 installed, and run `pip install -r requirements.txt` to install all Python dependencies.

**Note:** Make sure you have `libssl-dev` and `libffi-dev` installed on Debian (or the equivelant package for your distro) or installation of some dependencies may not work correctly.

### Configuration

Rename the `config.json.example` file to `config.json` and modify it to suit your needs, or view Cardinal's command line options with `./cardinal -h`.

You should also add your nick and vhost to the `plugins/admin/config.json` file in the format `nick@vhost` in order to take advantage of admin-only commands.

### Running

Running Cardinal is as simple as typing `./cardinal.py`.

## Writing Plugins

Cardinal plugins are designed to be simple to write while still providing tons of power. Here's a sample to show what a very simple plugin might look like:
```python
from cardinal.decorators import command, help

class HelloWorldPlugin(object):
	@command(['hello', 'hi'])
	@help("Responds to the user with a greeting.")
	@help("Syntax: .hello")
    def hello(self, cardinal, user, channel, msg):
        nick, ident, vhost = user.group(1), user.group(2), user.group(3)
        cardinal.sendMsg(channel, "Hello %s!" % nick)

def setup():
    return HelloWorldPlugin()
```

While it's not difficult to write plugins for Cardinal, lots of optional functionality is provided, and thus this section is too large to include in the README. Please [visit the wiki](https://github.com/JohnMaguire/Cardinal/wiki/Writing-Plugins) to learn about writing plugins.

## Contributing

If you have found a bug, feel free to submit a patch or simply open an issue on this repository.

If you're submitting a pull request, you may add your name to the CONTRIBUTORS file with a separate commit in the same branch as your modification.

Cardinal is a public, open-source project, licensed under the MIT License. Anyone may contribute.
