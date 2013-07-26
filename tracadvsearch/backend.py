"""
Backends for TracAdvancedSearchPlugin which implement IAdvSearchBackend.
"""
import datetime
import itertools
import pysolr
import re
import time

from advsearch import SearchBackendException
from interface import IAdvSearchBackend
from trac.config import ConfigurationError
from trac.core import Component
from trac.core import implements
from trac.search import shorten_result

class PySolrSearchBackEnd(Component):
	"""AdvancedSearchBackend that uses pysolr lib to search Solr."""
	implements(IAdvSearchBackend)

	SOLR_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
	INPUT_DATE_FORMAT = "%a %b %d %Y"

	SPECIAL_CHARACTERS = r'''+-&|!(){}[]^"~*?:\\'''
	ESCAPE_PATTERN = re.compile('[%s]' % re.escape(SPECIAL_CHARACTERS))

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

	@classmethod
	def escape(cls, s):
		return cls.ESCAPE_PATTERN.sub('\\\1', s)

	def query_backend(self, criteria):
		"""Send a query to solr."""

		q = {}
		params = {
			'fl': '*,score', # fields returned
			'rows': criteria.get('per_page', 15),
		}

		if criteria.get('sort_order') == 'oldest':
			params['sort'] = 'time asc'
		elif criteria.get('sort_order') == 'newest':
			params['sort'] = 'time desc'
		else: # sort by relevance
			# field boosts
			params['qf'] = '"name^3 token_text"'
			# phrase boosts
			params['pf'] = '"name token_text^3"'

		# try to find a start offset
		start_point = criteria['start_points'].get(self.get_name())
		if start_point:
			params['start'] = start_point

		# add all fields
		q['source'] = self._string_from_filters(criteria.get('source'))
		q['author'] = self._string_from_input(criteria.get('author'))
		q['time'] = self._date_from_range(
			criteria.get('date_start'),
			criteria.get('date_end')
		)

		# only include key/value pairs when the value is not empty
		q_parts = []
		for k, v in itertools.ifilter(lambda (k, v): v, q.iteritems()):
			q_parts.append('%s:%s' % (k, v))

		# Ticket only filters
		status = self._string_from_filters(criteria.get('ticket_statuses'))
		q_parts.append('(status:%s OR source:"wiki")' % status)

		# distribute our search query to several fields
		if 'q' in criteria:
			field_parts = []
			field_parts.append('token_text:(%(q)s)' % criteria)
			field_parts.append('name:(%(q)s)' % criteria)
			# include only digits, but preserve whitespace
			digit_query = re.sub('[^0-9 ]', '', criteria['q']).strip()
			if digit_query:
				field_parts.append('ticket_id:(%s)' % digit_query)

			q_parts.append('(%s)' % ' OR '.join(field_parts))

		if q_parts:
			q_string = " AND ".join(q_parts)
		else:
			q_string = '*:*'

		try:
			results = self.conn.search(q_string, **params)
		except pysolr.SolrError, e:
			raise SearchBackendException(e)
		for result in results:
			result['title'] = result['name']
			result['summary'] = self._build_summary(result.get('text'), criteria['q'])
			result['date'] = self._date_from_solr(result['time'])
			del result['time']
			del result['name']

		return (results.hits, results.docs)

	def _build_summary(self, text, query):
		"""Build a summary which highlights the search terms."""
		if not query:
			return text[:500]
		if not text:
			return ''

		return shorten_result(text, query.split(), maxlen=500)

	def _date_from_solr(self, date_string):
		"""Return a human friendly date from solr date string."""
		date = self._strptime(date_string, self.SOLR_DATE_FORMAT)
		return date.strftime(self.INPUT_DATE_FORMAT)

	def _string_from_input(self, value):
		"""Return a value string formatted in solr query syntax."""
		if not value:
			return None

		if type(value) in (list, tuple):
			return "(%s)" % (" OR ".join(['"%s"' % v for v in value if v]))

		return value

	def _string_from_filters(self, filter_list):
		if not filter_list:
			return None

		name_list = [f['name'] for f in filter_list if f['active']]
		if not name_list:
			return None

		# add filters that are set as active
		return '("%s")' % ('" OR "'.join(name_list))

	def _date_from_range(self, start, end):
		"""Return a date range in solr query syntax."""
		if not start and not end:
			return None

		if start:
			start_formatted = self._format_date(start)
		else:
			start_formatted = "*"
		if end:
			end_formatted = self._format_date(end)
		else:
			end_formatted = "*"
		return "[%s TO %s]" % (start_formatted, end_formatted)

	def _format_date(self, date_string, default="*"):
		"""Format a date as a solr date string."""
		try:
			date = self._strptime(
				date_string, self.INPUT_DATE_FORMAT)
		except ValueError:
			self.log.warn("Invalid date format: %s" % date_string)
			return default
		return date.strftime(self.SOLR_DATE_FORMAT)

	def _strptime(self, date_string, date_format):
		return datetime.datetime(*(time.strptime(date_string, date_format)[0:6]))

