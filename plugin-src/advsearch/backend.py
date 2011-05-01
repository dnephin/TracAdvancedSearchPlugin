"""
Backends for TracAdvancedSearchPlugin which implement IAdvSearchBackend.
"""
import datetime
import itertools
import pysolr

from trac.core import Component
from trac.core import implements
from advsearch import IAdvSearchBackend


# TODO: connect handling ?
# TODO: configure connection string to trac.ini
conn = pysolr.Solr('http://localhost:8983/solr/')

class PySolrBackEnd(Component):
	"""AdvancedSearchBackend that uses pysolr lib to search Solr."""
	implements(IAdvSearchBackend)

	SOLR_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
	INPUT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
	
	def get_name(self):
		return self.__class__.__name__

	def upsert_document(self, doc):
		# TODO:
		pass

	def query_backend(self, criteria):
		"""Send a query to solr."""
	
		q = {}
		params = {'fl': '*,score'}
		# try to find a start offset
		start_point = criteria['start_points'].get(self.get_name())
		if start_point:
			params['start'] = start_point

		# add all fields
		q['token_text'] = criteria.get('q')
		# TODO : add to schema
#		q['source'] = self._string_from_input(criteria.get('source'))
		q['author'] = self._string_from_input(criteria.get('author'))
		q['time'] = self._date_from_range(
			criteria.get('date_start'),
			criteria.get('date_end')
		)
	
		# only include key/value pairs when the value is not empty
		q_pairs = []
		for k, v in itertools.ifilter(lambda (k, v): v, q.iteritems()):
			q_pairs.append("%s: %s" % (k, v))

		# TODO: function query
		
		results = conn.search(" AND ".join(q_pairs), **params)
		for result in results:
			result['title'] = result['id']
			result['summary'] = result['text'][:200]
			result['source'] = 'wiki'
			result['date'] = self._date_from_solr(result['time'])
			del result['time']
			del result['id']
			del result['text']

		return (results.hits, results.docs)


	def _date_from_solr(self, date_string):
		date = datetime.datetime.strptime(date_string, self.SOLR_DATE_FORMAT)
		return date.strftime(self.INPUT_DATE_FORMAT)

	def _string_from_input(self, value):
		"""Return a value string formatted in solr query syntax."""
		if not value:
			return None

		if type(value) in (list, typle):
			return "(%s)" % (" OR ".join(value))

		return value

	def _date_from_range(self, start, end):
		"""Return a date range in solr query syntax."""
		if not start and not end:
			return None

		def format(date_string):
			try:
				date = datetime.datetime.strptime(
					date_string, self.INPUT_DATE_FORMAT)
			except ValueError:
				self.log.warn("Invalid date format: %s" % date_string)
				return "*"
			return date.strftime(self.SOLR_DATE_FORMAT)

		start_formatted = format(start) if start else "*"
		end_formatted = format(end) if end else "*"
		return "[%s TO %s]" % (start_formatted, end_formatted)

