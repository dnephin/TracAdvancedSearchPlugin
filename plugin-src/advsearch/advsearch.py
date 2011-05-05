"""
advsearch.py - Advanced Search Plugin for Trac

This module defines a Trac extension point for the advanced search backend.

See TracAdvancedSearchBackend for more details.
"""

from operator import itemgetter
import pkg_resources
import re
import simplejson

from genshi.builder import tag
from trac.perm import IPermissionRequestor
from trac.ticket.api import ITicketChangeListener
from trac.web.chrome import INavigationContributor
from trac.web.chrome import ITemplateProvider
from trac.web.main import IRequestHandler
from trac.wiki.api import IWikiChangeListener
from trac.wiki.api import IWikiSyntaxProvider

from trac.core import Component
from trac.core import ExtensionPoint
from trac.core import implements
from trac.util.html import html
from trac.util.presentation import Paginator
from trac.util.translation import _
from trac.web.chrome import add_stylesheet, add_warning, add_script
from interface import IAdvSearchBackend


class SearchBackendException(Exception):
	"""
	Raised by SearchBackends when there is a problem completeing the search
	query or indexing.
	"""


class AdvancedSearchPlugin(Component):
	implements(
		INavigationContributor, 
		IPermissionRequestor,
		IRequestHandler,
		ITemplateProvider,
		ITicketChangeListener,
		IWikiChangeListener,
		IWikiSyntaxProvider,
	)
	
	providers = ExtensionPoint(IAdvSearchBackend)

	SOURCE_FILTERS = ('wiki', 'ticket')
	DEFAULT_PER_PAGE = 10

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
		try:
			per_page = int(req.args.getfirst('per_page', 
				self.DEFAULT_PER_PAGE))
		except ValueError:
			self.log.warn('Could not set per_page to %s' % 
					req.args.getfirst('per_page'))
			per_page = self.DEFAULT_PER_PAGE

		try:
			page = int(req.args.getfirst('page', 1))
		except ValueError:
			page = 1

		data = {
			'source': self._get_filter_dicts(req.args),
			'author': [auth for auth in req.args.getlist('author') if auth],
			'date_start': req.args.getfirst('date_start'),
			'date_end': req.args.getfirst('date_end'),
			'q': query,
			'start_points': StartPoints.parse_args(req.args, self.providers),
			'per_page': per_page
		}

		if not query:
			return self._send_response(req, data)

		# perform query using backend if q is set
		result_map = {}
		total_count = 0
		for provider in self.providers:
			result_count, result_list = 0, []
			try:
				result_count, result_list = provider.query_backend(data)
			except SearchBackendException, e:
				add_warning(req, _('SearchBackendException: %s' % e))
			total_count += result_count
			result_map[provider.get_name()] = result_list

		if not result_count:
			return self._send_response(req, data)

		data['page'] = page
		results = self._merge_results(result_map, per_page)
		self._add_href_to_results(results)
		data['results'] = Paginator(
			results, 
			page=page-1, 
			max_per_page=per_page, 
			num_items=total_count
		)

		# pagination next/prev links
		if data['results'].has_next_page:
			data['start_points'] = StartPoints.format(results, data['start_points'])
		
		return self._send_response(req, data)

	def _send_response(self, req, data):
		"""Send the response."""

		# look for warnings
		if not len(self.providers):
			add_warning(req, _('No advanced search providers found. ' +
				'You must register a search backend.'))

		if data.get('results') and not len(data['results']):
			add_warning(req, _('No results.'))
			
		add_stylesheet(req, 'common/css/search.css')
		add_stylesheet(req, 'advsearch/css/advsearch.css')
		add_script(req, 'advsearch/js/advsearch.js')
		return 'advsearch.html', data, None

	def _merge_results(self, result_map, per_page):
		"""
		Merge results from multiple sources by score in each result. Return
		the search results to display to the user
		
		Example:
		[
			{
				'title': 'Trac Help', 
				'href': 'http://...', 
				'date': '2011-04-20 12:34:00', 
				'author': 'admin',
				'summary': '...'
			},
			...
		]
		"""
		# add backend_name as a key to each result and merge lists
		all_results = []
		for backend_name, results in result_map.iteritems():
			for result_dict in results:
				result_dict['backend_name'] = backend_name
			all_results.extend(results)
				
		# sort and return results for the page
		all_results.sort(key=itemgetter('score'), reverse=True)
		return all_results[:per_page]

	def _add_href_to_results(self, results):
		"""Add an href key/value to each result dict based on source."""
		for result in results:
			if result['source'] == 'wiki':
				result['href'] = self.env.href.wiki(result['title'])
			if result['source'] == 'ticket':
				result['href'] = self.env.href.ticket(result['ticket_id'])

	def _get_filter_dicts(self, req_args):
		"""Map filters to filter dicts for the frontend."""
		return [
			{'name': filter, 'active': req_args.get(filter)}
			for filter in self.SOURCE_FILTERS
		]

	# ITemplateProvider methods
	def get_htdocs_dirs(self):
		return [('advsearch', pkg_resources.resource_filename(__name__, 'htdocs'))]

	def get_templates_dirs(self):
		return [pkg_resources.resource_filename(__name__, 'templates')]

	# IWikiSyntaxProvider methods
	def get_wiki_syntax(self):
		return []
		
	def get_link_resolvers(self):
		yield ('advsearch', self._format_link)

	def _format_link(self, formatter, ns, target, label):
		path, query, fragment = formatter.split_link(target)
		if query:
			href = formatter.href.advsearch() + query.replace(' ', '+')
		else:
			href = target
		return tag.a(label, class_='search', href=href)

	# IWikiChangeListener methods
	def _update_wiki_page(self, page):
		doc = {
			'source': 'wiki',
			'id': 'wiki_%s' % page.name,
		}
		for prop in ('name', 'version', 'time', 'author', 'text', 'comment'):
			doc[prop] = getattr(page, prop)
		for provider in self.providers:
			try:
				provider.upsert_document(doc)
			except SearchBackendException, e:
				self.log.error('SearchBackendException: %s' % e)

	def _delete_wiki_page(self, name):
		identifier = 'wiki_%s' % (name)
		for provider in self.providers:
			try:
				provider.delete_document(identifier)
			except SearchBackendException, e:
				self.log.error('SearchBackendException: %s' % e)

	wiki_page_added = _update_wiki_page
	wiki_page_version_deleted = _update_wiki_page
	wiki_page_deleted = lambda self, page: self._delete_wiki_page(page.name)

	def wiki_page_changed(self, page, version, t, comment, author, ipnr):
		self._update_wiki_page(page)

	def wiki_page_renamed(self, page, old_name):
		self._delete_wiki_page(old_name)
		self._update_wiki_page(page)

	# ITicketChangeListener methods
	def ticket_created(self, ticket):
		from trac.ticket.api import TicketSystem 
		print TicketSystem(self.env).get_ticket_fields()
		print ticket
		print ticket.values
		doc = {
			'id': 'ticket_%s' % ticket.id,
			'ticket_id': ticket.id,
			'source': 'ticket',
			'author': ticket['reporter'],
			'ticket_version': ticket['version'],
			'name': ticket['summary'],
			'text': ticket['description'],
		}
		for prop in (
			'type', 
			'time', 
			'changetime', 
			'component', 
			'severity', 
			'priority',
			'owner',
			'milestone',
			'status',
			'resolution',
			'keywords'
		):
			doc[prop] = ticket[prop]
		for provider in self.providers:
			try:
				provider.upsert_document(doc)
			except SearchBackendException, e:
				self.log.error('SearchBackendException: %s' % e)
		
	def ticket_deleted(self, ticket):
		identifier = 'ticket_%s' % (ticket.id)
		for provider in self.providers:
			try:
				provider.delete_document(identifier)
			except SearchBackendException, e:
				self.log.error('SearchBackendException: %s' % e)

	def ticket_changed(self, ticket, comment, author, old_values):
		self.ticket_created(ticket)


class StartPoints(object):
	"""Format and parse start points for search."""

	FORMAT_STRING = 'provider_start_point:%s'

	@classmethod
	def parse_args(cls, req_args, provider_list):
		"""Return a dict of start points by provider from request args."""
		start_points = {}
		for provider in provider_list:
			start_points[provider.get_name()] = req_args.getfirst(
				cls.FORMAT_STRING % provider.get_name(), 
				0
			)
		return start_points

	@classmethod
	def format(cls, results, prev_start_points):
		"""Return dict of start_point name to value."""
		start_points = {}
		for result in results:
			backend_name = result['backend_name']
			if not backend_name in start_points:
				try:
					prev_start = int(prev_start_points.get(backend_name, 0))
				except:
					prev_start = 0
				start_points[backend_name] = prev_start
			start_points[backend_name] += 1

		return simplejson.dumps(
			[
				{
					'name': cls.FORMAT_STRING % name,
					'value': value
				} 
				for (name, value) in start_points.iteritems()
			]
		)
