import subprocess

from base import OSAbstractionLayer

class NTAbstractionLayer(OSAbstractionLayer):
	def set_admin_password(self, password):
		args = ('net', 'user', 'Administrator', password)
		
		self.log.debug('exec "%s"', ' '.join(args))

		pwchange = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		stdout, stderr = pwchange.communicate()

		if pwchange.returncode:
			raise OSError(pwchange.returncode, 'error while executing "net user..."', stderr.rstrip())
