import os

if os.name == 'nt':
	from nt import NTAbstractionLayer
	osal = NTAbstractionLayer()
# Unix-like OS are not yet supported
#elif os.name == 'unix':
#	from unix import UnixAbstractionLayer as OSAbstractionLayer
else:
	raise TypeError('Running on an unsupported OS ({0})'.format(os.name))
