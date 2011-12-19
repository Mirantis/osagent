#!/usr/bin/env python
import os.path

from distutils.core import setup
from py2exe2msi import py2exe2msi, Service


PACKAGE_NAME = 'OpenStackAgent'
VERSION = '0.0.4'
COMPANY_NAME = 'Mirantis'

package_metadata = dict(
	name = PACKAGE_NAME,
	version = VERSION,
	description = '<description>',
	author = COMPANY_NAME,
	author_email = 'abyss@mirantis.com',
	long_description = '''<long-description>''',
	classifiers = [
		'License :: Other/Proprietary License',
		'Programming Language :: Python',
		'Development Status :: 3 - Alpha',
		'Intended Audience :: Developers',
		'Operating System :: Microsoft :: Windows',
	],
	license = 'Proprietary License'
)

NtService = Service(
	name = 'OpenStackAgent',
	display_name = 'OpenStack Agent Service',
	version = VERSION,
	company_name = COMPANY_NAME,
	# used for the versioninfo resource
	description = 'OpenStack Agent service',
	# what to build.  For a service, the module name (not the
	# filename) must be specified!
	modules = ['NtService'],
	install = dict(
		start_type = Service.START_AUTO,
		error = Service.ERROR_IGNORE
	),
	control = dict(
		start_on = Service.INSTALL,
		stop_on = Service.INSTALL,
		remove_on = Service.UNINSTALL,
		wait = False
	)
)

setup(
	options = dict(
		py2exe = dict(
			compressed = 1,  # create a compressed zip archive
			optimize = 2,
			excludes = ['pywin', 'pywin.debugger', 'pywin.debugger.dbgcon', 'pywin.dialogs', 'pywin.dialogs.list']
		),
		py2exe2msi = dict(
			pfiles_dir = 'OpenStackAgent',
			upgrade_code = '{BF9C41BE-9C81-42CD-A1CB-A8C17699A2F1}'
		)
	),
	# The lib directory contains everything except the executables and the python dll.
	# Can include a subdirectory name.
	zipfile = 'lib/shared.zip',
	data_files = [
		('.', [os.path.join(os.path.dirname(__file__), 'NtService.logging.json')])
	],
	service = [NtService],
	**package_metadata
)
