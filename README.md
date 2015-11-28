# Meet Cardinal.
Cardinal is your new best friend and personal assistant on IRC. A modular, Twisted-based Python IRC bot, Cardinal has plenty of common features (such as a calculator, fetching of page titles, etc.) as well as some more interesting ones (integration with Last.fm and YouTube searching.) If you're a developer, it's easy to create your own plugins in a matter of minutes.

Cardinal development channel on IRC: [irc.darkscience.org:+6697/cardinal](irc://irc.darkscience.org:+6697/cardinal)

## What can Cardinal do?
Out of the box Cardinal can...

* Grab the page titles for links
* Search for YouTube videos and link them in chat
* Tell you the weather
* Show who's listening to what with Last.fm integration
* Message you with a time-based reminder
* Act as a calculator and unit/currency converter
* Save "notes" -- effectively turns Cardinal into an info bot
* Grab definitions from Urban Dictionary
* ... and more!

But Cardinal is still in active development! Features are being added as quickly as they can be thought up and coded. It's also easy to write your own plugins for even more functionality.

## Basic Usage
### Installation
It is recommended that you install and use Cardinal inside of a [Python virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/). You can do so by running the following command inside of your cloned repository.

`virtualenv -p /usr/bin/python2.7 . && source bin/activate`

In the future, you will just have to remember to call `source bin/activate` before using Cardinal.

### Dependencies
Make sure you have Python 2.7 installed, and run `pip install -r requirements.txt` to install all Python dependencies.

**Note:** Make sure you have `libssl-dev` and `libffi-dev` installed on Debian (or the equivelant package for your distro) or installation of some dependencies may not work correctly.

### Running
Running Cardinal is as simple as typing `./cardinal.py`. Before running Cardinal, you should ensure that you have set your network settings in the `config.json` file, or run `./cardinal.py -h` to use command line arguments to set the network and channels you would like Cardinal to connect to.

You should also add your nick and vhost to the `plugins/admin/config.json` file in the format `nick@vhost` in order to take advantage of admin-only commands.

## Writing Plugins
Cardinal plugins are designed to be simple to write while still providing tons of power. Here's a sample to show what a very simple plugin might look like:
```python
class HelloWorldPlugin(object):
    def hello(self, cardinal, user, channel, msg):
        nick, ident, vhost = user.group(1), user.group(2), user.group(3)
        cardinal.sendMsg(channel, "Hello %s!" % nick)
    hello.commands = ['hello', 'hi']
    hello.help = ["Responds to the user with a greeting.",
                  "Syntax: .hello"]

def setup():
    return HelloWorldPlugin()
```

While it's not difficult to write plugins for Cardinal, lots of optional functionality is provided, and thus this section is too large to include in the README. Please [visit the wiki](https://github.com/JohnMaguire/Cardinal/wiki/Writing-Plugins) to learn about writing plugins.

## Contributing
If you have found a bug, feel free to submit a patch or simply open an issue on this repository and I will get to it as soon as possible. Be sure to add your name to the CONTRIBUTORS file in a separate commit on the same branch as your modification so that I can give credit where credit is due.

Cardinal is a public, open-source project, licensed under the MIT License. Anyone may contribute.
