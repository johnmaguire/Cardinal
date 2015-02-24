import os
import sys
import re
import logging
import sqlite3

HELP_REGEX = re.compile(r'^!(.+?)')

class NotesPlugin(object):
    logger = None

    def __init__(self, cardinal):
        # Initialize logging
        self.logger = logging.getLogger(__name__)

        # Connect to or create the note database
        self._connect_or_create_db(cardinal)

    def _connect_or_create_db(self, cardinal):
        try:
            self.conn = sqlite3.connect(os.path.join(
                cardinal.storage_path,
                'notes-%s.db' % cardinal.network
            ))
        except Exception, e:
            self.conn = None
            self.logger.exception("Unable to access local notes database")
            return

        c = self.conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS notes (title text collate nocase, content text collate nocase)")
        self.conn.commit()

    def add_note(self, cardinal, user, channel, msg):
        if not self.conn:
            cardinal.sendMsg("Unable to access notes database.")
            return

        message = msg.split('=', 1)
        title_message = message[0].split(' ', 1)
        if (len(message) < 2 or
            len(title_message) < 2 or
            len(message[1]) == 0):

            cardinal.sendMsg(channel, "Syntax: .addnote <title>=<content>")
            return

        title = title_message[1]
        content = message[1]

        c = self.conn.cursor()
        c.execute("INSERT INTO notes (title, content) VALUES(?, ?)", (title, content))
        self.conn.commit()

        cardinal.sendMsg(channel, "Saved note '%s'." % title)

    add_note.commands = ['addnote']
    add_note.help = ["Saves a note to the database for retrieval later.",
                     "Syntax: .addnote <title>=<content>"]

    def get_note(self, cardinal, user, channel, msg):
        if not self.conn:
            cardinal.sendMsg(channel, "Unable to access notes database.")
            return

        message = msg.split(' ', 1)
        # Check if they are using ! syntax.
        if message[0][0] == '!':
            title = ' '.join(message)[1:]
        else:
            if len(message) != 2:
                cardinal.sendMsg(channel, "Syntax: .note <title>")
                return

            # Grab title for .note syntax.
            title = message[1]

        c = self.conn.cursor()
        c.execute("SELECT COUNT(title)t FROM notes WHERE title=?", (title,))
        result = c.fetchone()

        if not result[0]:
            cardinal.sendMsg(channel, "No notes found under '%s'." % title)
            return

        count = result[0]

        c.execute("SELECT content FROM notes WHERE title=? ORDER BY RANDOM() LIMIT 1", (title,))
        result = c.fetchone()

        content = bytes(result[0])

        cardinal.sendMsg(channel, "%s (%d): %s" % (title, count, content))

    get_note.commands = ["note"]
    get_note.regex = HELP_REGEX
    get_note.syntax = ["Retrieve a saved note.",
                       "Syntax: .note <title>"]

def setup(cardinal):
    return NotesPlugin(cardinal)
