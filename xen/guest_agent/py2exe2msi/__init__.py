import os
import sys
import types
import msilib

import distutils

from distutils import log
from distutils.command.bdist_msi import bdist_msi
from distutils.dir_util import remove_tree
from distutils.version import StrictVersion
from distutils.errors import DistutilsOptionError

import py2exe

import schema
import sequence
import utils


class Service(py2exe.build_exe.Target, object):
	# See http://msdn.microsoft.com/en-us/library/windows/desktop/aa371637%28v=VS.85%29.aspx for details
	# A service start during startup of the system.
	START_AUTO = 0x00000002
	# A service start when the service control manager calls the StartService function.
	START_DEMAND = 0x00000003
	# Specifies a service that can no longer be started.
	START_DISABLED = 0x00000004

	# Logs the error and continues with the startup operation.
	ERROR_IGNORE = 0x00000000
	# Logs the error, displays a message box and continues the startup operation.
	ERROR_NORMAL = 0x00000001
	# Logs the error if it is possible and the system is restarted with the last configuration known to be good.
	# If the last-known-good configuration is being started, the startup operation fails.
	ERROR_CRITICAL = 0x00000003

	TYPE_OWN_PROCESS = 0x00000010  # A Microsoft Win32 service that runs its own process.
	TYPE_SHARE_PROCESS = 0x00000020  # A Win32 service that shares a process.

	# A Win32 service that interacts with the desktop.
	# This value cannot be used alone and must be added to one of the two previous types.
	# The StartName column must be set to LocalSystem or null when using this flag.
	_INTERACTIVE_PROCESS = 0x00000100

	INSTALL = 0x1
	UNINSTALL = 0x2

	# Starts the service during the StartServices action.
	_msidbServiceControlEventStart = 0x001
	# Stops the service during the StopServices action.
	_msidbServiceControlEventStop = 0x002
	# Deletes the service during the DeleteServices action.
	_msidbServiceControlEventDelete = 0x008
	# Starts the service during the StartServices action.
	_msidbServiceControlEventUninstallStart = 0x010
	# Stops the service during the StopServices action.
	_msidbServiceControlEventUninstallStop = 0x020
	# Deletes the service during the DeleteServices action.
	_msidbServiceControlEventUninstallDelete = 0x080

	@staticmethod
	def get_dest_file(self):
		# NOTE: we do not support other than own process (.exe) services
		return '{0}.exe'.format(self.get_dest_base())


class py2exe2msi(bdist_msi, object):
	description = 'build a msi containing the py2exe compiled binaries'

	user_options = [
		('skip-build', None, 'skip rebuilding everything (for testing/debugging)'),
		('keep-temp', 'k', 'keep the pseudo-installation tree around after creating the distribution archive'),
	]

	FEATURE_ID = 'DefaultFeature'
	FEATURE_TITLE = ''
	FEATURE_DESCRIPTION = ''

	def initialize_options(self):
		self.keep_temp = 0
		self.skip_build = 0

		self.target_version = None
		self.pfiles_dir = None
		# TODO: replace with correct identifier (os.name or something)
		self.plat_name = 'win32'
		self.product_code = None
		self.upgrade_code = None

	def finalize_options(self):
		self.bdist_dir = self.get_finalized_command('py2exe').dist_dir
		self.dist_dir = '.'

		if self.pfiles_dir is None:
			raise DistutilsOptionError('invalid Program Files subdirectory: %r', self.pfiles_dir)

	def run(self):
		if not (os.path.isdir(self.bdist_dir) and self.skip_build):
			self.run_command('py2exe')

		fullname = self.distribution.get_fullname()
		installer_name = self.get_installer_filename(fullname)
		installer_name = os.path.abspath(installer_name)

		if os.path.exists(installer_name):
			os.unlink(installer_name)

		metadata = self.distribution.metadata
		author = metadata.author

		if not author:
			author = metadata.maintainer
		if not author:
			author = 'UNKNOWN'

		version = metadata.get_version()
		sversion = '%d.%d.%d' % StrictVersion(version).version
		product_name = self.distribution.get_name()

		log.info('creating MSI package %s', installer_name)

		self.db = msilib.init_database(installer_name, schema,
				product_name, self.product_code or msilib.gen_uuid(), sversion, author)

		msilib.add_tables(self.db, sequence)

		props = []

		if self.upgrade_code:
			props.extend([
				('UpgradeCode', self.upgrade_code),
				('SecureCustomProperties', 'REPLACE')
			])

			msilib.add_data(self.db, 'Upgrade', [(
				self.upgrade_code,  # UpgradeCode
				None,  # VersionMin, detect all
				sversion,  # VersionMax
				None,  # Language
				0,  # Attributes
				None,  # Remove, REMOVE=ALL
				'REPLACE'  # ActionProperty
			)])

		if props:
			msilib.add_data(self.db, 'Property', props)

		self.add_files()
		self.add_services()

		self.db.Commit()

		if not self.keep_temp:
			remove_tree(self.bdist_dir, dry_run=self.dry_run)
			remove_tree(self.get_finalized_command('build').build_base)

	def add_files(self):
		db = self.db
		cab = msilib.CAB('distfiles')

		prog_files_dir = msilib.Directory(db, cab,
			_logical = 'ProgramFilesFolder', default = 'PFiles', physical = '',
			basedir = msilib.Directory(db, cab,
				_logical = 'TARGETDIR', default = 'SourceDir', physical = '', basedir = None)
		)

		root_dir = msilib.Directory(db, cab,
			_logical = 'AppDir',
			default = '{0}|{1}'.format(prog_files_dir.make_short(self.pfiles_dir), self.pfiles_dir),
			physical = self.bdist_dir,
			basedir = prog_files_dir
		)

		feature = msilib.Feature(db, self.FEATURE_ID, self.FEATURE_TITLE, self.FEATURE_DESCRIPTION, 0)

		make_id = utils.IdGenerator()

		self.cfiles = dict()

		todo = [root_dir]

		def _cab_gen_id(absolute, file):
			return cab.__class__.gen_id(cab, file)
		# NOTE: a bit of monkeypatching, a workaround for the bug in
		# msilib.Directory.start_component when keyfile parameter is present
		cab.gen_id = _cab_gen_id

		while todo:
			dir = todo.pop()

			log.info('adding %s\\', dir.absolute)

			for file in os.listdir(dir.absolute):
				abs_file = os.path.join(dir.absolute, file)
				if os.path.isdir(abs_file):
					# postponing directory processing
					todo.append(
						msilib.Directory(db, cab,
							dir, file, file, '{0}|{1}'.format(dir.make_short(file), file)))
				else:
					file_path = os.path.join(dir.absolute, file)
					log.info('adding %s', file_path)

					file_id = make_id(file)
					self.cfiles[file_path] = file_id

					dir.start_component(file_id, feature, 0, keyfile = file)
					dir.add_file(file)

		db.Commit()
		cab.commit(db)

	def add_services(self):
		def get_service_comp(service):
			dest_file = os.path.join(self.bdist_dir, Service.get_dest_file(service))
			return self.cfiles[dest_file]

		def install_service(service):
			log.info('adding installer for %s service', service.name)
			comp_id = get_service_comp(service)

			msilib.add_data(self.db, 'ServiceInstall', [(
				comp_id,  # ServiceInstall
				service.name,  # Name
				# DisplayName
				getattr(service, 'display_name', service.name),
				Service.TYPE_OWN_PROCESS,  # ServiceType
				# ServiceType
				getattr(service.install, 'start', Service.START_AUTO),
				# ErrorControl
				getattr(service.install, 'error', Service.ERROR_NORMAL),
				None,  # LoadOrderGroup
				None,  # Dependencies
				None,  # StartName
				None,  # Password
				None,  # Arguments
				comp_id,  # Component_
				getattr(service, 'description', None)  # Description
			)])

		def control_service(service):
			start_on = service.control.get('start_on', 0)
			stop_on = service.control.get('stop_on', 0)
			remove_on = service.control.get('remove_on', 0)

			if not (start_on or stop_on or remove_on):
				log.warn('skipping controller for %s service, no events specified', service.name)
			else:
				log.info('adding controller for %s service', service.name)

			comp_id = get_service_comp(service)

			event = (
			(Service._msidbServiceControlEventStart if start_on & Service.INSTALL else 0) |
			(Service._msidbServiceControlEventStop if stop_on & Service.INSTALL else 0) |
			(Service._msidbServiceControlEventDelete if remove_on & Service.INSTALL else 0) |
			(Service._msidbServiceControlEventUninstallStart if start_on & Service.UNINSTALL else 0) |
			(Service._msidbServiceControlEventUninstallStop if stop_on & Service.UNINSTALL else 0) |
			(Service._msidbServiceControlEventUninstallDelete if remove_on & Service.UNINSTALL else 0))

			msilib.add_data(self.db, 'ServiceControl', [(
				comp_id,  # ServiceControl
				service.name,  # Name
				event,  # Event
				'~'.join(service.control.get('args', [])),  # Arguments
				1 if service.control.get('wait', True) else 0,  # Wait
				comp_id  # Component_
			)])

		for service in self.distribution.service:
			if hasattr(service, 'install'):
				try:
					install_service(service)
				except Exception as error:
					log.error('error while adding service installer for %s: %s', service.name, str(error))
					continue
			if hasattr(service, 'control'):
				try:
					control_service(service)
				except Exception as error:
					log.error('error while adding service controller for %s: %s', service.name, str(error))
					continue

		self.db.Commit()

distutils.command.__all__.append('py2exe2msi')
sys.modules['distutils.command.py2exe2msi'] = sys.modules[__name__]
