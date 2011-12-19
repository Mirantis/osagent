import json
import weakref

import log
from xen import XenStore, XenStoreError


class Command(object):
	# TODO: investigate if these values must be of int type, however works for now
	RET_OK = '0'
	RET_UNSUPPORTED = '1'
	RET_UNKNOWN = '500'

	_subclasses = dict()

	def __id__(self):
		return self.uuid

	def __init__(self, queue, uuid, args):
		self.queue = queue
		self.uuid = uuid
		self.args = args

	def _exec(self, args):
		raise NotImplemented()

	def __call__(self):
		self.queue.log.debug('exec %s', self)
		try:
			result = self._exec(self.args)
		except CommandError as error:
			self.queue.log.error('%s (uuid=%s)', error, self.uuid)
			self.queue._command_return(self.uuid, error.code, message = error.message)
		except Exception as error:
			self.queue.log.exception('exception while executing (uuid=%s)', self.uuid)
		else:
			if isinstance(result, CommandResult):
				self.queue._command_return(self.uuid, result.code, result.message)
			else:
				self.queue._command_return(self.uuid, Command.RET_OK, result)

	def __str__(self):
		return '{0}<{1}>'.format(self.__class__.__name__, self.uuid)

	@staticmethod
	def register(name):
		def registrar(cls):
			Command._subclasses[name] = cls
		return registrar


class CommandError(Exception):
	def __init__(self, message, code = Command.RET_UNKNOWN, output = None):
		super(CommandError, self).__init__(message)
		self.code = code
		self.output = output

	def __str__(self):
		return '{0} (code={1})'.format(self.message, self.code)


class CommandResult(object):
	def __init__(self, code = Command.RET_OK, message = None):
		self.code = code
		self.message = message

	def __str__(self):
		return '{0}<{1}, {2}>'.format(self.__class__.__name__, self.code, self.message)

class CommandQueue(object):
	log = log.getLogger('cmd.q')

	def __init__(self, xen_store):
		self.xen_store = xen_store
		self.pending = weakref.WeakValueDictionary()

	def __iter__(self):
		try:
			uuid_list = self.xen_store.dir(XenStore.HOST_DATA)
		except XenStoreError as error:
			if error.returncode == 1:
				return
			else:
				raise

		self.log.debug('got %d commands pending', len(uuid_list))

		for uuid in uuid_list:
			if uuid in self.pending:
				self.log.debug('ignoring (uuid=%s), pending already', uuid)
				continue

			self.log.debug('reading (uuid=%s)', uuid)
			try:
				data = self.xen_store.read(XenStore.join(XenStore.HOST_DATA, uuid))
			except XenStoreError as error:
				self.log.error('error reading (uuid=%s): %s', UUID, str(error))
				continue

			self.log.debug(repr(data))
			try:
				data = json.loads(''.join(s.rstrip() for s in data.splitlines()))
			except Exception as error:
				self.log.error('error decoding (uuid=%s): %s', uuid, str(error), exc_info=True)
				continue

			try:
				class_name = data.pop('name')
			except KeyError:
				self.log.error('invalid object, name missing (uuid=%s)', uuid)
				continue

			try:
				value = data.pop('value')
			except KeyError:
				self.log.error('invalid object, value missing (uuid=%s)', uuid)
				continue

			try:
				command_class = Command._subclasses[class_name]
			except KeyError:
				self.log.warning('unsupported: %s (uuid=%s)', class_name, uuid)
				self._command_return(uuid, Command.RET_UNSUPPORTED, 'unsupported command: {0}'.format(class_name))
				continue

			try:
				command = command_class(self, uuid, value)
			except Exception as error:
				self.log.exception()
				continue

			self.pending[command.uuid] = command
			yield command

	def _command_return(self, uuid, returncode, message = None):
		self.log.debug('returning code %s (uuid=%s)', str(returncode), uuid)
		response = json.dumps(dict(returncode = returncode, message = message))
		self.xen_store.write(XenStore.join(XenStore.GUEST_DATA, uuid), response)

		self.log.debug('removing command from queue (uuid=%s)', uuid)
		self.xen_store.remove(XenStore.join(XenStore.HOST_DATA, uuid))


@Command.register('features')
class FeaturesCommand(Command):
	def _exec(self, args):
		return ','.join(Command._subclasses.keys())
