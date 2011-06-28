"""
Backends for TracAdvancedSearchPlugin which implement IAdvSearchBackend.
"""
import datetime
import itertools
import pysolr

from trac.config import ConfigurationError
from trac.core import Component
from trac.core import implements
from interface import IAdvSearchBackend
from advsearch import SearchBackendException

class PySolrSearchBackEnd(Component):
	"""AdvancedSearchBackend that uses pysolr lib to search Solr."""
	implements(IAdvSearchBackend)

	SOLR_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
	INPUT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

	def __init__(self):
		solr_url = self.config.get('pysolr_search_backend', 'solr_url', None)
		timeout = self.config.getfloat('pysolr_search_backend', 'timeout', 30)
		if not solr_url:
			raise ConfigurationError('PySolrSearchBackend must be configured in trac.ini')
		self.conn = pysolr.Solr(solr_url, timeout=timeout)

	def get_name(self):
		"""Return friendly name for this IAdvSearchBackend provider."""
		return self.__class__.__name__

	def get_sources(self):
		return ('wiki', 'ticket')

	def upsert_document(self, doc):
		doc['time'] = doc['time'].strftime(self.SOLR_DATE_FORMAT)
		try:
			self.conn.add([doc])
		except pysolr.SolrError, e:
			raise SearchBackendException(e)

	def delete_document(self, identifier):
		try:
			self.conn.delete(id=identifier)
		except pysolr.SolrError, e:
			raise SearchBackendException(e)

	def query_backend(self, criteria):
		"""Send a query to solr."""

		q = {}
		params = {
			'fl': '*,score',
			'rows': criteria.get('per_page', 10)
		}
		# try to find a start offset
		start_point = criteria['start_points'].get(self.get_name())
		if start_point:
			params['start'] = start_point

		# add all fields
		q['token_text'] = criteria.get('q')
		q['source'] = self._string_from_filters(criteria.get('source'))
		q['author'] = self._string_from_input(criteria.get('author'))
		q['time'] = self._date_from_range(
			criteria.get('date_start'),
			criteria.get('date_end')
		)

		# only include key/value pairs when the value is not empty
		q_parts = []
		for k, v in itertools.ifilter(lambda (k, v): v, q.iteritems()):
			q_parts.append("%s: %s" % (k, v))

		# Ticket only filters
		status = self._string_from_filters(criteria.get('ticket_statuses'))
		q_parts.append("(status: %s OR source: wiki)" % status)

		q_string = " AND ".join(q_parts) if q_parts else '*:*'

		try:
			results = self.conn.search(q_string, **params)
		except pysolr.SolrError, e:
			raise SearchBackendException(e)
		for result in results:
			result['title'] = result['name']
			# TODO: better summary
			result['summary'] = result['text'][:500]
			result['date'] = self._date_from_solr(result['time'])
			del result['time']
			del result['text']
			del result['name']

		return (results.hits, results.docs)

	def _date_from_solr(self, date_string):
		"""Return a human friendly date from solr date string."""
		date = datetime.datetime.strptime(date_string, self.SOLR_DATE_FORMAT)
		return date.strftime(self.INPUT_DATE_FORMAT)

	def _string_from_input(self, value):
		"""Return a value string formatted in solr query syntax."""
		if not value:
			return None

		if type(value) in (list, tuple):
			return "(%s)" % (" OR ".join([v for v in value if v]))

		return value

	def _string_from_filters(self, filter_list):
		if not filter_list:
			return None

		name_list = [f['name'] for f in filter_list if f['active']]
		if not name_list:
			return None

		# add filters that are set as active
		return "(%s)" % (" OR ".join(name_list))

	def _date_from_range(self, start, end):
		"""Return a date range in solr query syntax."""
		if not start and not end:
			return None

		start_formatted = self._format_date(start) if start else "*"
		end_formatted = self._format_date(end) if end else "*"
		return "[%s TO %s]" % (start_formatted, end_formatted)

	def _format_date(self, date_string, default="*"):
		"""Format a date as a solr date string."""
		try:
			date = datetime.datetime.strptime(
				date_string, self.INPUT_DATE_FORMAT)
		except ValueError:
			self.log.warn("Invalid date format: %s" % date_string)
			return default
		return date.strftime(self.SOLR_DATE_FORMAT)

