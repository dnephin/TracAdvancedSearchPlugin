from setuptools import setup

PACKAGE = 'TracAdvancedSearch'
VERSION = '0.5'

setup(name=PACKAGE,
	version=VERSION,
	packages=['tracadvsearch'],
	entry_points={'trac.plugins': '%s = tracadvsearch' % PACKAGE},
	package_data={
		'tracadvsearch': [
			'templates/*.html',
			'htdocs/css/*.css',
			'htdocs/js/*.js'
		]
	},
)
