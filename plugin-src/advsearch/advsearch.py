"""
 advsearch.py - Advanced Search Plugin for Trac
"""

import pkg_resources
import re

from trac.perm import IPermissionRequestor
from trac.web.chrome import INavigationContributor
from trac.web.chrome import ITemplateProvider
from trac.web.main import IRequestHandler
from trac.wiki.api import IWikiSyntaxProvider

from trac.core import Component
from trac.core import implements
from trac.util import escape
from trac.util.html import html
from trac.util.translation import _
from trac.web.chrome import add_link, add_stylesheet, add_warning

class AdvancedSearchPlugin(Component):
	implements(
		INavigationContributor, 
		IPermissionRequestor,
		IRequestHandler,
		IWikiSyntaxProvider,
		ITemplateProvider,
	)

	# INavigationContributor methods
	def get_active_navigation_item(self, req):
		return 'advsearch'

	def get_navigation_items(self, req):
		if 'SEARCH_VIEW' in req.perm:
			yield ('mainnav', 
				'advsearch', 
				html.A(_('Advanced Search'), href=self.env.href.advsearch())
			)

	# IPermissionRequestor methods
	def get_permission_actions(self):
		return ['SEARCH_VIEW']

	# IRequestHandler methods
	def match_request(self, req):
		# TODO: add /search if search module is disabled
		return re.match(r'/advsearch?', req.path_info) is not None

	def process_request(self, req):
		req.send_response(200)
		abuffer = 'Hello world!'
		req.send_header('Content-Type', 'text/plain')
		req.send_header('Content-length', str(len(abuffer)))
		req.end_headers()
		req.write(abuffer)

	# ITemplateProvider methods
	def get_htdocs_dirs(self):
		return []

	def get_templates_dirs(self):
		return [pkg_resources.resource_filename(__name__, 'templates')]

	# IWikiSyntaxProvider methods
	def get_wiki_syntax(self):
		return []
		
	def get_link_resolvers(self):
		# TODO
		return []
