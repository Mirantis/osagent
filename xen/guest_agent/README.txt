OpenStackAgent Service
======================

Building
--------

_Requirements_

1. ActiveState Python version 2.7 installed.
Downloadable from: http://www.activestate.com/activepython/downloads
Make sure that _32-bit_ version is used.

2. PyCrypto library for Windows compatible with Python installation above.
Downloadable from: http://www.voidspace.org.uk/python/modules.shtml#pycrypto

3. py2exe library
Downloadable from: http://sourceforge.net/projects/py2exe/files/

_Instructions_

1. Just run "python <path-to-OpenStackAgent-source>\setup.py py2exe2msi"
2. Find the compiled distribution at <your-current-working-dir>\OpenStackAgent-<version>.<platform>.msi

Installation and Running
------------------------

_Requirements_

1. Xen Guest Utilities installed

2. VC2008 SP1 Run\time installed
Downloadable from: http://www.microsoft.com/download/en/details.aspx?displaylang=en&id=29

_Instructions_

1. Just run the installation package, it will be installed/upgraded automatically
