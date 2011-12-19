import os
import base64
import hashlib
import binascii

from Crypto.Cipher import AES

from . import log, Command, CommandError, CommandResult
from osal import osal

class PasswordExchange(object):
	def __init__(self, *args, **kwargs):
		# prime to use
		self.prime = 162259276829213363391578010288127
		self.base = 5
		self.kwargs = {}
		self.kwargs.update(kwargs)

	def _mod_exp(self, num, exp, mod):
		result = 1
		while exp > 0:
			if (exp & 1) == 1:
				result = (result * num) % mod
			exp = exp >> 1
			num = (num * num) % mod
		return result

	def _make_private_key(self):
		"""
		Create a private key using /dev/urandom
		"""
		return int(binascii.hexlify(os.urandom(16)), 16)

	def _dh_compute_public_key(self, private_key):
		"""
		Given a private key, compute a public key
		"""
		return self._mod_exp(self.base, private_key, self.prime)

	def _dh_compute_shared_key(self, public_key, private_key):
		"""
		Given public and private keys, compute the shared key
		"""
		return self._mod_exp(public_key, private_key, self.prime)

	def _compute_aes_key(self, key):
		"""
		Given a key, compute the corresponding key that can be used
		with AES
		"""
		m = hashlib.md5()
		m.update(key)

		aes_key = m.digest()

		m = hashlib.md5()
		m.update(aes_key)
		m.update(key)

		aes_iv = m.digest()

		self.aes_key = (aes_key, aes_iv)

	def _decrypt_password(self, aes_key, data):
		aes = AES.new(aes_key[0], AES.MODE_CBC, aes_key[1])
		passwd = aes.decrypt(data)

		cut_off_sz = ord(passwd[len(passwd) - 1])
		if cut_off_sz > 16 or len(passwd) < 16:
			raise ValueError('Invalid password data received')

		return passwd[:-cut_off_sz]

	def _decode_password(self, data):
		try:
			real_data = base64.b64decode(data)
		except Exception:
			raise ValueError('Couldn\'t decode base64 data')

		try:
			aes_key = self.aes_key
		except AttributeError:
			raise TypeError('Password without key exchange')

		return self._decrypt_password(aes_key, real_data)

	def _wipe_key(self):
		"""
		Remove key from a previous keyinit command
		"""
		try:
			del self.aes_key
		except AttributeError:
			pass

PEX = PasswordExchange()


class AuthCommand(Command):
	log = log.getLogger('cmd.auth')


@Command.register('keyinit')
class KeyInitCommand(AuthCommand):
	def _exec(self, data):
		# Remote pubkey comes in as large number

		# Or well, it should come in as a large number.  It's possible
		# that some legacy client code will send it as a string.  So,
		# we'll make sure to always convert it to long.
		self.log.info('exchanging password keys')

		remote_public_key = long(data)

		my_private_key = PEX._make_private_key()
		my_public_key = PEX._dh_compute_public_key(my_private_key)

		shared_key = str(PEX._dh_compute_shared_key(remote_public_key, my_private_key))

		PEX._compute_aes_key(shared_key)

		# The key needs to be a string response right now
		return CommandResult('D0', str(my_public_key))


class PasswordChangeError(CommandError):
	pass


@Command.register('password')
class PasswordCommand(AuthCommand):
	def _exec(self, data):
		password = PEX._decode_password(data)

		self.log.info('setting password (%d chars)', len(password))

		try:
			osal.set_admin_password(password)
		except OSError as error:
			self.log.exception('failed to set password', exc_info=True)
			raise PasswordChangeError('unable to change password', output = str(error))

		PEX._wipe_key()
