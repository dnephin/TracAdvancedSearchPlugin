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
	
	SOURCE_FILTERS = ('wiki', 'ticket')

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
		"""
		Implements IRequestHandler.process_request

		Build a dict of search criteria from the user and request results from 
		the active AdvancedSearchBackend.
		"""
		req.perm.assert_permission('SEARCH_VIEW')

		query = req.args.get('q')
		data = {
			'source_filters': self._get_filter_dicts(self.SOURCE_FILTERS, req.args),
			'author_filters': req.args.getlist('author_filters'),
			'date_range_start': req.args.getfirst('date_range_start'),
			'date_range_end': req.args.getfirst('date_range_end'),
			'query': query, 
			'quickjump': None, 
			'results': []
		}

		add_stylesheet(req, 'common/css/search.css')
		return 'advsearch.html', data, None

	@classmethod
	def _get_filter_dicts(cls, filter_list, req_args):
		return [
			{'name': filter, 'active': req_args.get(filter)}
			for filter in filter_list
		]

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
