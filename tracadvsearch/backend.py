"""
Backends for TracAdvancedSearchPlugin which implement IAdvSearchBackend.
"""
import datetime
import itertools
import locale
import pysolr
import sys
import threading
import time
import Queue
from operator import methodcaller

from advsearch import SearchBackendException
from interface import IAdvSearchBackend
from interface import IIndexer
from trac.config import ConfigurationError
from trac.core import Component
from trac.core import implements
from trac.search import shorten_result

CONFIG_SECTION_NAME = 'pysolr_search_backend'
CONFIG_FIELD = {
	'solr_url': (
		CONFIG_SECTION_NAME,
		'solr_url',
		None,
	),
	'timeout': (
		CONFIG_SECTION_NAME,
		'timeout',
		30,
	),
	'async_indexing': (
		CONFIG_SECTION_NAME,
		'async_indexing',
		False,
	),
	'async_queue_maxsize': (
		CONFIG_SECTION_NAME,
		'async_queue_maxsize',
		0,
	),
}


def _get_incremental_value(initial, next_, step):
	""" return incremental value in two stage
	e.g.)
		- step = 0 or 1, return 10
		- step >= 2, return 30
	>>> g = _get_incremental_value(10, 30, 2)
	>>> g.next()
	10
	>>> g.next()
	10
	>>> g.next()
	30
	"""
	for i in itertools.count():
		if i < step:
			yield initial
		else:
			yield next_


class SolrIndexer(object):
	"""Synchronous Indexer for PySolrSearchBackEnd."""
	implements(IIndexer)

	def __init__(self, backend):
		self.backend = backend

	def upsert(self, doc):
		try:
			self.backend.conn.add([doc])
		except pysolr.SolrError, e:
			raise SearchBackendException(e)

	def delete(self, identifier):
		try:
			self.backend.conn.delete(id=identifier)
		except pysolr.SolrError, e:
			raise SearchBackendException(e)


class SimpleLifoQueue(list):

	def __init__(self, maxsize=0):
		self.maxsize = maxsize

	def put(self, item):
		if len(self) >= self.maxsize:
			raise Queue.Full
		self.append(item)

	def get(self):
		if len(self) > 0:
			return self.pop()
		return None

	def empty(self):
		return len(self) == 0


class AsyncSolrIndexer(threading.Thread):
	"""Asynchronous Indexer for PySolrSearchBackEnd."""
	implements(IIndexer)

	SLEEP_INTERVAL = (60, 3600, 10)

	def __init__(self, backend, maxsize):
		self.backend = backend
		self.queue = Queue.Queue(maxsize)
		self.recovery_queue = SimpleLifoQueue(maxsize)
		threading.Thread.__init__(self)
		self._name = self.__class__.__name__

	def run(self):
		prev_available = False
		interval = self.interval_generator
		while True:
			while self.is_available():
				self.indexing()
				if not prev_available:
					interval = self.interval_generator
					prev_available = True
			else:
				prev_available = False
				time.sleep(interval.next())

	def indexing(self):
		def get_item():
			if self.recovery_queue.empty():
				return self.queue.get(block=True)
			else:
				return self.recovery_queue.get()

		try:
			method_name, item = get_item()
			methodcaller(method_name, item)(self)
		except Exception, e:
			self.backend.log.exception(e)
			try:
				self.recovery_queue.put((method_name, item))
			except Queue.Full, e:
				_msg = '%s: Recovery Queue is full, cannot put: %s'
				self.backend.log.error(_msg % (self._name, item))
		else:
			self.queue.task_done()

	@property
	def interval_generator(self):
		return _get_incremental_value(*self.SLEEP_INTERVAL)

	def is_available(self):
		available = False
		try:
			path = '/admin/ping?wt=json'
			res = self.backend.conn._send_request('get', path)
			json = self.backend.conn.decoder.decode(res)
			available = json.get('status') == 'OK'
			if not available:
				self.backend.log.warn('%s: Solr is not available: %s' % (self._name, r))
		except Exception, e:
			self.backend.log.error('%s: Solr may be down: %s' % (self._name, e))
		return available

	def upsert(self, doc):
		try:
			self.queue.put(('upsert_index', doc), block=False)
		except Queue.Full, e:
			self.backend.log.error('%s: Queue is full, cannot put: %s' % (self._name, doc))

	def upsert_index(self, doc):
		self.backend.log.debug('%s: upsert id=%s' % (self._name, doc.get('id')))
		self.backend.conn.add([doc])

	def delete(self, identifier):
		try:
			self.queue.put(('delete_index', identifier), block=False)
		except Queue.Full, e:
			self.backend.log.error('%s: Queue is full, cannot put: %s' % (self._name, identifier))

	def delete_index(self, identifier):
		self.backend.log.debug('%s: delete id=%s' % (self._name, identifier))
		self.backend.conn.delete(id=identifier)


class PySolrSearchBackEnd(Component):
	"""AdvancedSearchBackend that uses pysolr lib to search Solr."""
	implements(IAdvSearchBackend)

	SOLR_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
	INPUT_DATE_FORMAT = "%a %b %d %Y"
	DEFAULT_DATE_ENCODING = "utf-8"

	SPECIAL_CHARACTERS = r'''+-&|!(){}[]^"~*?:\\'''

	def __init__(self):
		solr_url = self.config.get(*CONFIG_FIELD['solr_url'])
		timeout = self.config.getfloat(*CONFIG_FIELD['timeout'])
		if not solr_url:
			raise ConfigurationError('PySolrSearchBackend must be configured in trac.ini')
		self.conn = pysolr.Solr(solr_url, timeout=timeout)

		self.async_indexing = self.config.getbool(*CONFIG_FIELD['async_indexing'])
		if self.async_indexing:
			maxsize = self.config.getint(*CONFIG_FIELD['async_queue_maxsize'])
			self.indexer = AsyncSolrIndexer(self, maxsize)
			self.indexer.start()
		else:
			self.indexer = SolrIndexer(self)

	def get_name(self):
		"""Return friendly name for this IAdvSearchBackend provider."""
		return self.__class__.__name__

	def get_sources(self):
		return ('wiki', 'ticket')

	def upsert_document(self, doc):
		doc['time'] = doc['time'].strftime(self.SOLR_DATE_FORMAT)
		self.indexer.upsert(doc)

	def delete_document(self, identifier):
		self.indexer.delete(identifier)

	def query_backend(self, criteria):
		"""Send a query to solr."""

		q = {}
		params = {
			'fl': '*,score', # fields returned
			'rows': criteria.get('per_page', 15),
			# see https://cwiki.apache.org/confluence/display/solr/The+DisMax+Query+Parser
			'defType': 'edismax',
			# favor phrases in the ticket body, exact matches in the name
			'pf': 'token_text name^2 ticket_id',
			'qf': 'token_text name^2 ticket_id component milestone keywords',

		}

		if criteria.get('sort_order') == 'oldest':
			params['sort'] = 'time asc'
		elif criteria.get('sort_order') == 'newest':
			params['sort'] = 'time desc'
		else: # sort by relevance
			pass

		# try to find a start offset
		start_point = criteria['start_points'].get(self.get_name())
		if start_point:
			params['start'] = start_point

		# add all fields
		q['source'] = self._string_from_filters(criteria.get('source')) or '("wiki" OR "ticket")'
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
		params['fq'] = '(status:(%s) OR source:"wiki")' % status

		# distribute our search query to several fields
		if 'q' in criteria and criteria['q']:
			# edismax handles escaping for us
			q_parts.append('(%s)' % criteria['q'])
		else:
			q_parts.append('*:*')

		q_string = " AND ".join(q_parts)

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
		def safe_decode(date_string):
			if isinstance(date_string, str):
				lang, encoding = locale.getlocale()
				encoding = encoding if encoding else self.DEFAULT_DATE_ENCODING
				return unicode(date_string, encoding)
			return date_string

		date = self._strptime(date_string, self.SOLR_DATE_FORMAT)
		return safe_decode(date.strftime(self.INPUT_DATE_FORMAT))

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

