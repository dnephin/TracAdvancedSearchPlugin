# -*- coding: utf-8 -*-
import sys

from setuptools import setup

PACKAGE = 'TracAdvancedSearch'
VERSION = '0.5.3'

try:
	LONG_DESCRIPTION = ''.join([
		open('README').read(),
	])
except:
	LONG_DESCRIPTION = ''

REQUIRES = [
	'Trac >= 0.11',
	'pysolr',
]

if sys.version_info[:2] < (2, 6):
	REQUIRES.append('simplejson')

CLASSIFIERS = [
	'Framework :: Trac',
	'Development Status :: 4 - Beta',
	'Environment :: Web Environment',
	'Intended Audience :: Developers',
	'Operating System :: OS Independent',
	'Programming Language :: Python',
	'Topic :: Software Development',
]

setup(name=PACKAGE,
	version=VERSION,
	description='This plugin allows you to index your wiki and ticket data '
		    'in a full text search engine and search it from a button '
		    'in the main navbar.',
	long_description=LONG_DESCRIPTION,
	classifiers=CLASSIFIERS,
	keywords=['trac', 'plugin', 'search', 'full-text-search'],
	author='Daniel Nephin',
        author_email='dnephin at gmail.com',
	url='http://trac-hacks.org/wiki/TracAdvancedSearchPlugin',
	license='SEE LICENSE',
        platforms=['linux', 'osx', 'unix', 'win32'],
	packages=['tracadvsearch'],
	entry_points={'trac.plugins': '%s = tracadvsearch' % PACKAGE},
	package_data={
		'tracadvsearch': [
			'templates/*.html',
			'htdocs/css/*.css',
			'htdocs/js/*.js'
		]
	},
	include_package_data=True,
	install_requires=REQUIRES,
)
