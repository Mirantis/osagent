import gc
import log

from xen import XenStore
from commands import CommandQueue, auth, update


class AgentService(object):
	log = log.getLogger()

	def __init__(self, logging_config):
		log.configure(logging_config)
		self.log.debug('initializing')
		self.command_queue = CommandQueue(XenStore())

	def run(self):
		self.log.info('starting up')

		while not self.should_stop():
			for command in self.command_queue:
				command()
			
			self.log.debug('collecting garbage')
			gc.collect()

		self.log.info('stopping gracefully')

	def should_stop(self):
		raise NotImplemented()
