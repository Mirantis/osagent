import hashlib
import os.path
import subprocess

from . import log, Command, CommandError, CommandResult


class AgentUpdateError(CommandError):
	pass

@Command.register('agentupdate')
class AgentUpdateCommand(Command):
	log = log.getLogger('agup')
	@classmethod
	def fetch_file(cls, url, block_size = 4096):
		with closing(urllib2.urlopen(url)) as src:
				file_size = src.info().get('Content-Length', None)
				bytes_read = 0
				if not file_size is None:
						file_size = int(file_size)

				with tempfile.NamedTemporaryFile(delete = False) as dst:
						self.log.info('fetching %s into %s (%s bytes to read)', url, dst.name, file_size or '?')

						md5sum = hashlib.md5()
						while True:
								data = src.read(block_size)
								if not data: break
								bytes_read += len(data)
								md5sum.update(data)
								dst.write(data)

						log.debug('done fetching, %d bytes read', bytes_read)
						return dst.name, md5sum.hexdigest()

	def handle_archive_msi(self, filename):
		subprocess.Popen(('msiexec', '/i', '/q', filename))

	def _exec(self, data):
		if isinstance(data, str):
			url, md5sum = data.split(',', 1)
		elif isinstance(data, dict):
			try:
				url, md5sum = data['url'], data['md5sum']
			except KeyError:
				raise AgentUpdateError('missing URL or MD5 sum in arguments')

		file, file_md5sum = self.fetch_file(url)
		if md5sum != file_md5sum:
			raise AgentUpdateError('MD5 sum mismatch')

		path, ext = os.path.splitext(file)

		handler = getattr(self, 'handle_archive_{0}'.format(ext), None)
		if handler is None:
			raise AgentUpdateError('unsupported update format: .{0}'.format(ext))

		self.log.info('updating agent')
		return handler(file)

