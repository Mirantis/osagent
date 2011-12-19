from msilib.sequence import *


UI_SEQ_EXCLUDE = ('ExitDialog', 'FatalError', 'UserExit')


def filter_sequence(seq, exclude):
	for item in seq:
		if item[0] not in exclude:
			yield item

AdminUISequence = list(filter_sequence(AdminUISequence, UI_SEQ_EXCLUDE))
InstallUISequence = list(filter_sequence(InstallUISequence, UI_SEQ_EXCLUDE))
