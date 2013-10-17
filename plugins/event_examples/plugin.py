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

# NOTE: Any events may be named however you would like. To flag something as
# an event, simply register it with one of the following command attributes:
#
# - on_join
# - on_part
# - on_quit
# - on_kick
# - on_action
# - on_topic
# - on_nick
#
# Please note that due to limitations imposed by the Twisted IRC library, the
# only event that returns a full user group (1 => nick, 2 => username,
# 3 => hostname) is the on_action event.
#
# All other functions will give you a nickname only!
class EventExamplesPlugin(object):
    # This method may be named anything you'd like.
    def user_joined(self, cardinal, nick, channel):
        cardinal.sendMsg(channel, "Welcome %s! :)" % (nick,))

    # Set the on_join attribute on a method to true for it to be to triggered
    # when a user joins a channel.
    user_joined.on_join = True

    # This method may be named anything you'd like.
    def user_left(self, cardinal, nick, channel):
        cardinal.sendMsg(channel, "Goodbye %s. :(" % (nick,))

    # Set the on_part attribute on a method to true for it to be to triggered
    # when a user leaves a channel.
    user_left.on_part = True

    # This method may be named anything you'd like.
    # NOTE: There is no channel value given for this function because a QUIT
    # is broadcasted over the server, not the channel.
    def user_quit(self, cardinal, nick, message):
        cardinal.sendMsg("#bots", "%s quit the server saying: %s. D:" % (nick, message))

    # Set the on_quit attribute on a method to true for it to be to triggered
    # when a user quits the server.
    user_quit.on_quit = True

    # This method may be named anything you'd like.
    def user_kicked(self, cardinal, kicked, channel, kicker, message):
        cardinal.sendMsg(channel, "%s got kicked by %s! He shouldn't have '%s' on %s!" % (kicked, kicker, message, channel))

    # Set the on_kick attribute on a method to true for it to be to triggered
    # when a user is kicked from a channel.
    user_kicked.on_kick = True

    # This method may be named anything you'd like.
    def user_action(self, cardinal, user, channel, data):
        cardinal.sendMsg(channel, "%s just did WHAT? Did he really just '%s'?" % (user.group(1), data))

    # Set the on_action attribute on a method to true for it to be to triggered
    # when a user is kicked from a channel.
    user_action.on_action = True

    # This method may be named anything you'd like.
    def topic_change(self, cardinal, nick, channel, newTopic):
        cardinal.sendMsg(channel, "%s just changed the topic... it's now %s." % (nick, newTopic))

    # Set the on_topic attribute on a method to true for it to be to triggered
    # when a user is kicked from a channel.
    topic_change.on_topic = True

    # This method may be named anything you'd like.
    # NOTE: There is no channel value given for this function because a NICK
    # is broadcasted over the server, not the channel.
    def nick_change(self, cardinal, oldnick, newnick):
        cardinal.sendMsg("#bots", "%s is %s now? Who'da thunk." % (oldnick, newnick))

    # Set the on_nick attribute on a method to true for it to be to triggered
    # when a user is kicked from a channel.
    nick_change.on_nick = True

def setup(cardinal):
    return EventExamplesPlugin()
