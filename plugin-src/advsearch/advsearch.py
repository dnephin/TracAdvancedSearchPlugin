"""
 advsearch.py - Advanced Search Plugin for Trac
"""


from trac.core import Component
from trac.core import implements
from trac.web.chrome import INavigationContributor
from trac.web.main import IRequestHandler
from trac.util import escape
from trac.util.html import html

class AdvancedSearchPlugin(Component):
	implements(INavigationContributor, IRequestHandler)

	# INavigationContributor methods
	def get_active_navigation_item(self, req):
		return 'advsearch'

	def get_navigation_items(self, req):
		yield ('mainnav', 
			'advsearch', 
			html.A('Advanced Search', href=self.env.href.advsearch())
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
