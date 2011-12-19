from .. import log


class OSAbstractionLayer(object):
	log = log.getLogger('os')

	def set_admin_password(self, password):
		raise NotImplementedError()


class FakeOSAbstractionLayer(OSAbstractionLayer):
	def set_admin_password(self, password):
		pass
