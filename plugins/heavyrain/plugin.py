import random
import time
from twisted.internet import reactor

class HeavyRain(object):
	# A dictionary which will contain the owner nicks and vhosts
	owners = None

	# A list of trusted vhosts
	trusted_vhosts = None

	def __init__(self, cardinal):
		self.owners = {}
		self.trusted_vhosts = []
		self.cardinal = cardinal
		
	def config_owners(self):
		config = self.cardinal.config('admin')
		# If owners aren't defined, bail out
		if 'owners' not in config:
			return

		# Loop through the owners in the config file and add them to the
		# instance's owner array.
		for owner in config['owners']:
			owner = owner.split('@')
			self.owners[owner[0]] = owner[1]
			self.trusted_vhosts.append(owner[1])


	def is_owner(self, user):
		if len(self.owners) == 0:
			self.config_owners()

		if user.group(3) in self.trusted_vhosts:
			return True
		return False

	def handle_rain(self, user_list):
		for i in range(5):
			random_user = random.choice(user_list[self.heavy_channel])
			reactor.callLater(i*2, self.cardinal.sendMsg, self.heavy_channel, "&tip %s %s" % (random_user[0], 0.0001))
			#self.cardinal.sendMsg(self.heavy_channel, )

	def rain(self, cardinal, user, channel, msg):
		if self.is_owner(user):
			self.heavy_channel = channel
			cardinal.who(channel, self.handle_rain)
	rain.commands = ['heavy']

def setup(cardinal):
	return HeavyRain(cardinal)