"""
 advsearch.py - Advanced Search Plugin for Trac
"""


from trac.core import Component
from trac.core import implements
from trac.core import Markup

from trac.web.chrome import INavigationContributor
from trac.web.main import IRequestHandler
from trac.util import escape, Markup

class AdvancedSearchPlugin(Component):
	implements(INavigationContributor, IRequestHandler)

	# INavigationContributor methods
	def get_active_navigation_item(self, req):
		return 'advsearch'

	def get_navigation_items(self, req):
		yield ('mainnav', 
			'advsearch', 
			Markup('<a href="%s">Advanced Search</a>' % (self.env.href.helloworld()))
		)

	# IRequestHandler methods
	def match_request(self, req):
		return req.path_info == '/advsearch'

	def process_request(self, req):
		req.send_response(200)
		abuffer = 'Hello world!'
		req.send_header('Content-Type', 'text/plain')
		req.send_header('Content-length', str(len(abuffer)))
		req.end_headers()
		req.write(abuffer)
