import os
import re
import subprocess

import log


class XenStoreError(Exception, object):
	def __init__(self, message, command = None, xargs = None, returncode = None):
		super(XenStoreError, self).__init__(message)
		self.command = command
		self.returncode = returncode
		self.xargs = xargs


class XenStore(object):
	XENSTORE_CLIENT = r'{}\Citrix\XenTools\xenstore_client.exe'.format(
		os.environ.get('PROGRAMFILES(X86)', None) or os.environ.get('PROGRAMFILES')
	)

	CFG_DATA = 'vm-data'
	HOST_DATA = 'data/host'
	GUEST_DATA = 'data/guest'
	NETWORKING = 'networking'

	log = log.getLogger('xs')

	def __init__(self):
		self.log.info('using xenstore_client %s', self.XENSTORE_CLIENT)
		if not os.path.isfile(self.XENSTORE_CLIENT):
			raise XenStoreError('unable to locate xenstore_client utility')

	def dir(self, key):
		return self('dir', key).splitlines()

	def remove(self, key):
		self('remove', key)

	def write(self, key, value):
		self('write', key, XenStore._escape(value))

	def read(self, key):
		return self('read', key)

	@staticmethod
	def join(*args):
		return '/'.join(args)

	_re_quot = re.compile('"')

	@classmethod
	def _escape(cls, data):
		# no specific escaping is required
		return data
		#return cls._re_quot.sub(r'\"', data)

	def __call__(self, command, *args):
		xargs = [self.XENSTORE_CLIENT, command]
		xargs.extend(args)

		self.log.debug(' '.join(xargs))

		client = subprocess.Popen(xargs, stdout = subprocess.PIPE)
		(stdout, stderr) = client.communicate()
		if client.returncode:
			error_message = '{0} ({1})'.format(stdout.rstrip(), client.returncode)
			self.log.error(error_message)
			raise XenStoreError(error_message, command = command, xargs = xargs, returncode = client.returncode)

		return stdout
