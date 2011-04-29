from setuptools import setup

PACKAGE = 'TracAdvancedSearch'
VERSION = '0.1'

setup(name=PACKAGE,
	version=VERSION,
	packages=['advsearch'],
	entry_points={'trac.plugins': '%s = advsearch' % PACKAGE},
)
