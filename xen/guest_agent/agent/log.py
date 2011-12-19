import os
import json
import logging
import logging.config


def configure(filename = os.path.join(os.path.dirname(__file__), 'logging.json')):
	with open(filename, 'rt') as config_file:
		config_data = json.load(config_file)

	logging.config.dictConfig(config_data)

# TODO: support Python 2.6 as well
class DictConfigurator(logging.config.DictConfigurator):
	value_converters = dict(
		logging.config.DictConfigurator.value_converters,
		env = 'env_convert'
	)

	def env_convert(self, value):
		return os.path.expandvars(value)

getLogger = logging.getLogger
