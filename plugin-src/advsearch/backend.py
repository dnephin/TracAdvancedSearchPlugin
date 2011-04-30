"""
Backends for TracAdvancedSearchPlugin which implement IAdvSearchBackend.
"""
from trac.core import Component
from trac.core import implements
from advsearch import IAdvSearchBackend

import pysolr

# TODO: connect handling ?
# TODO: configure connection string to trac.ini
conn = pysolr.Solr('http://localhost:8983/solr/')

class PySolrBackEnd(Component):
	"""AdvancedSearchBackend that uses pysolr lib to search Solr."""
	implements(IAdvSearchBackend)

	def get_name(self):
		return self.__class__.__name__

	def upsert_document(self, doc):
		# TODO:
		pass

	def query_backend(self, criteria):
		# TODO		
		results = conn.search('*:*', fl='*,score')
		for result in results:
			result['title'] = result['id']
			result['summary'] = result['text'][:200]
			result['source'] = 'wiki'
			del result['id']
			del result['text']

		return (results.hits, results.docs)
#		return (1,
#			[
#				{
#					'title': 'TracHelp', 
#					'score': 0.876, 
#					'source': 'wiki', 
#					'date': '2011-02-34 23:34',
#					'author': 'admin',
#					'summary': '==Trac Help== ....'
#				},
#			]
#		)

