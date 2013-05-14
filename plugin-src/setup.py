from setuptools import setup

PACKAGE = 'TracAdvancedSearch'
VERSION = '0.5.3'

setup(name=PACKAGE,
	version=VERSION,
    author="Daniel Nephin",
    author_email="dnephin@gmail.com",
    url="http://github.com/dnephin/TracAdvancedSearchPlugin",
	packages=['tracadvsearch'],
	entry_points={'trac.plugins': '%s = tracadvsearch' % PACKAGE},
	package_data={
		'tracadvsearch': [
			'templates/*.html',
			'htdocs/css/*.css',
			'htdocs/js/*.js'
		]
	},
    install_requires=[
        'pysolr>=2.0.14',
        'trac>=0.12',
    ]
)
