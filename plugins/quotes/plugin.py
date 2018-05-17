import sqlite3, logging, random, os

class QuotesPlugin(object):
    logger = None

    def __init__(self, cardinal):
        self.logger = logging.getLogger(__name__)
        self._connect_or_create_db(cardinal)

    def _get_admins(self, cardinal):
        admin_config = cardinal.config('admin')
        # If admins aren't defined, bail out
        if admin_config is not None and 'admins' in admin_config:
            admins = []
            for admin in admin_config['admins']:
                admin = admin.split('@')
                admins.append(admin[1])

            return admins

    def _connect_or_create_db(self, cardinal):
        try:
            self.conn = sqlite3.connect(os.path.join(
                cardinal.storage_path,
                'database',
                'quotes-%s.db' % cardinal.network
            ))
        except Exception:
            self.conn = None
            self.logger.exception("Unable to access local quotes database")
            return

        c = self.conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS quotes ("
                  "id integer PRIMARY KEY, "
                  "content text collate nocase, "
                  "user text collate nocase)")
        self.conn.commit()

    def add_quote(self, cardinal, user, channel, msg):
        msg = msg.split(' ', 2)

        if len(msg) < 3 or len(msg[2].strip()) == 0:
            cardinal.sendMsg(channel, "Syntax: .quote add <content>")
            return

        content = msg[2]

        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO quotes(content, user) VALUES(?, ?)",
                  (content, user.group(1)))
        self.conn.commit()

        cardinal.sendMsg(channel, "Saved quote.")

    def del_quote(self, cardinal, user, channel, msg):
        if user.group(3) in self._get_admins(cardinal):
            msg = msg.split(' ', 2)

            if len(msg) < 3 or len(msg[2].strip()) == 0:
                cardinal.sendMsg(channel, "Syntax: .quote del <id>")
                return

            quote_id = msg[2]

            c = self.conn.cursor()
            c.execute("SELECT id FROM quotes WHERE id=?", (quote_id,))
            result = c.fetchone()

            if not result:
                cardinal.sendMsg(channel, "No quote found under id %s." % quote_id)
                return

            c.execute("DELETE FROM quotes WHERE id=?", (quote_id,))
            self.conn.commit()

            cardinal.sendMsg(channel, "Deleted quote saved under id %s." % quote_id)

    def search_quote(self, cardinal, user, channel, msg):
        msg = msg.split(' ', 2)

        if len(msg) < 3 or len(msg[2].strip()) == 0:
            cardinal.sendMsg(channel, "Syntax: .quote search <search string>")
            return

        search_string = msg[2]

        c = self.conn.cursor()
        c.execute("SELECT id, content FROM quotes WHERE content LIKE ?", ('%' + search_string + '%',))
        results = c.fetchall()

        refined_quotes = []

        for quote in results:
            refined_quotes.append('#%s: "%s..."' % (quote[0], ' '.join(quote[1].split()[:8])))

        cardinal.sendMsg(channel, "%s quotes found: %s." % (len(refined_quotes), bytes(', '.join(refined_quotes))))

    def get_quote(self, cardinal, user, channel, msg):
        msg = msg.split(' ', 2)

        if len(msg) < 3 or len(msg[2]) == 0:
            cardinal.sendMsg(channel, "Syntax: .quote get [random/<id>]")

        if msg[2] == "random":
            content = self._get_random_quote_from_db()
        else:
            content = self._get_quote_from_db(msg[2])

        if not content:
            cardinal.sendMsg(channel, "No quote found under id %s." % msg[2])
            return

        cardinal.sendMsg(channel, "Quote #%s: %s (added by %s)" % (bytes(content['id']), bytes(content['quote']), bytes(content['user'])))

    def count_quotes(self, cardinal, user, channel, msg):
        msg = msg.split(' ', 1)

        if len(msg) < 2 or len(msg[1]) == 0:
            cardinal.sendMsg(channel, "Syntax: .quote count")

        total_quotes = 0

        c = self.conn.cursor()
        for id in c.execute("SELECT id FROM quotes"):
            total_quotes += 1

        cardinal.sendMsg(channel, "I have %s quotes saved in my database." % total_quotes)

    def quote(self, cardinal, user, channel, msg):
        if not self.conn:
            cardinal.sendMsg(channel, "Unable to access quotes database.")
            return

        message = msg.split(' ', 2)

        if len(message) < 2 or len(message[1]) == 0:
            cardinal.sendMsg(channel, "Syntax: .quote [get/add/del/search/count]")
            return

        if message[1] == "get":
            self.get_quote(cardinal, user, channel, msg)
        elif message[1] == "add":
            self.add_quote(cardinal, user, channel, msg)
        elif message[1] == "del":
            self.del_quote(cardinal, user, channel, msg)
        elif message[1] == "count":
            self.count_quotes(cardinal, user, channel, msg)
        elif message[1] == "search":
            self.search_quote(cardinal, user, channel, msg)
        else:
            cardinal.sendMsg(channel, "Syntax: .quote [get/add/del/search/count]")

    quote.commands = ["quote"]
    quote.help = ["Quote system.",
                  "Syntax: .quote [get/add/del/search/count]"]


    def _get_random_quote_from_db(self):
        ids = []

        c = self.conn.cursor()
        for id in c.execute("SELECT id FROM quotes"):
            ids.append(id[0])

        return self._get_quote_from_db(random.choice(ids))

    def _get_quote_from_db(self, id):
        c = self.conn.cursor()
        c.execute("SELECT content,user FROM quotes WHERE id=?", (id,))
        result = c.fetchone()

        if not result:
            return False
        else:
            return {'id':id, 'quote':result[0], 'user': result[1]}

def setup(cardinal):
    return QuotesPlugin(cardinal)
