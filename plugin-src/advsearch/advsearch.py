"""
advsearch.py - Advanced Search Plugin for Trac

This module defines a Trac extension point for the advanced search backend.

See TracAdvancedSearchBackend for more details.
"""

import pkg_resources
import re

from trac.perm import IPermissionRequestor
from trac.web.chrome import INavigationContributor
from trac.web.chrome import ITemplateProvider
from trac.web.main import IRequestHandler
from trac.wiki.api import IWikiSyntaxProvider

from trac.core import Component
from trac.core import ExtensionPoint
from trac.core import implements
from trac.util import escape
from trac.util.html import html
from trac.util.translation import _
from trac.web.chrome import add_link, add_stylesheet, add_warning


class IAdvSearchBackend(Interface):
	"""Interface to provides a search service."""

	def upsert_document(doc):
		"""
		Accepts a dictionary doc which contains all the data about an updated
		document (wiki page, ticket, etc) to be inserted or updated in the 
		backend index. The keys of the dict should match the field names in
		the database.
		"""


	def query_backend(criteria):
		"""
		Given a dictionary of criteria, perform a query in the search backend
		and return a list of dicts with the results. Backends should ignore any
		criteria it does not know how to deal with.

		Returns a dict with keys: name, score, source, text.  When multiple 
		providers return results for a source score is used to order the results.

		Example:
		criteria = {
			'q': 'trac help',
			'author: ['admin', 'joe'],
			'source': ['wiki'],
			'date_start': '2011-04-01',
			'date_end': '2011-04-30',
		}

		return [
			{
				'name': 'TracHelp', 
				'score': 0.876, 
				'source': 'wiki', 
				'text': '==Trac Help== ....' 
			},
			...
		]
		"""


class AdvancedSearchPlugin(Component):
	implements(
		INavigationContributor, 
		IPermissionRequestor,
		IRequestHandler,
		IWikiSyntaxProvider,
		ITemplateProvider,
	)
	
	providers = ExtensionPoint(IAdvSearchBackend)

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
			'source': req.args.getlist('source_filters'),
			'author': req.args.getlist('author_filters'),
			'date_start': req.args.getfirst('date_range_start'),
			'date_end': req.args.getfirst('date_range_end'),
			'q': query, 
		}

		# perform query using backend
		result_map = {}
		for provider in self.providers:
			result_map[provider.__class__.__name__] = provider.query_backend(data)

		data['source_filters'] = self._get_filter_dicts(self.SOURCE_FILTERS, req.args)
		data['quickjump'] = None
		data['results'], data['start_points'] = self._merge_results(result_map)

		add_stylesheet(req, 'common/css/search.css')
		return 'advsearch.html', data, None

	def _merge_results(self, result_map):
		"""
		Merge results from multiple sources by score in each result. Return
		a tuple of (results, start_points).  Results is the list of search
		results to display to the user, and start points are the offsets
		to use on the next page of results.  These are only needed when
		multiple providers return results.
		
		Example:
		(
			// Results
			[
				{
					'title': 'Trac Help', 
					'href': 'http://...', 
					'date': '2011-04-20 12:34:00', 
					'author': 'admin',
					'summary': '...'
				},
				...
			],
			// Start points
			{
				'PySolrBackend': 8,
				'SphinxBackend': 4,
			}
		)
		"""



	def _get_filter_dicts(self, filter_list, req_args):
		"""Map filters to filter dicts for the frontend."""
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
