import re
import itertools


class IdGenerator(object):
	'''The Identifier data type is a text string.Identifiers may contain
	the ASCII characters A-Z (a-z), digits, underscores (_), or periods
	(.). However, every identifier must begin with either a letter or
	an underscore.
	See http://msdn.microsoft.com/en-us/library/Aa369212 for details
	'''
	def __init__(self):
		self._ids = set()
		self._suffix_gen = itertools.cycle(xrange(1024))

	_re_invalid = re.compile(r'[^\w\.]+', re.DOTALL)
	_re_valid_beg = re.compile('^[A-Za-z_]')

	def __call__(self, src):
		src = self._re_invalid.sub('_', src).upper()
		if not self._re_valid_beg.match(src):
			src = 'A_' + src

		suffix = ''
		while True:
			id = src if not suffix else '{0}.{1:x}'.format(src, suffix)
			if id not in self._ids:
				self._ids.add(id)
				return id

			suffix = next(self._suffix_gen)
