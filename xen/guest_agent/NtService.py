import sys
import os.path

import win32serviceutil
import win32service
import win32event
import win32evtlogutil

from agent.service import AgentService


class NtService(win32serviceutil.ServiceFramework):
	_svc_name_ = 'OpenStackAgent'
	_svc_display_name_ = 'OpenStack Agent Service'
	_svc_deps_ = ['EventLog']

	class Worker(AgentService):
		TIMEOUT = 5000

		BASE_DIR = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding())) if hasattr(sys, 'frozen') else os.path.dirname(unicode(__file__, sys.getfilesystemencoding()))
		LOGGING_CONF = os.path.join(BASE_DIR, 'NtService.logging.json')

		def __init__(self):
			super(NtService.Worker, self).__init__(self.LOGGING_CONF)
			self._stop_event = win32event.CreateEvent(None, 0, 0, None)

		def should_stop(self):
			return not bool(win32event.WaitForSingleObject(self._stop_event, self.TIMEOUT) == win32event.WAIT_TIMEOUT)

		def stop(self):
			win32event.SetEvent(self._stop_event)

	def __init__(self, args):
		win32serviceutil.ServiceFramework.__init__(self, args)
		self.worker = self.Worker()

	def SvcStop(self):
		self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
		self.worker.stop()

	def SvcDoRun(self):
		import servicemanager
		# Write a 'started' event to the event log...
		win32evtlogutil.ReportEvent(self._svc_name_,
									servicemanager.PYS_SERVICE_STARTED,
									0,  # category
									servicemanager.EVENTLOG_INFORMATION_TYPE,
									(self._svc_name_, ''))
		self.worker.run()

		# and write a 'stopped' event to the event log.
		win32evtlogutil.ReportEvent(self._svc_name_,
									servicemanager.PYS_SERVICE_STOPPED,
									0,  # category
									servicemanager.EVENTLOG_INFORMATION_TYPE,
									(self._svc_name_, ''))

if __name__ == '__main__':
	# Note that this code will not be run in the 'frozen' exe-file!!!
	win32serviceutil.HandleCommandLine(NtService)
