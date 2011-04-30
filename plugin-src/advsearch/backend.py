"""
Backends for TracAdvancedSearchPlugin which implement IAdvSearchBackend.
"""
from trac.core import Component
from trac.core import implements
from advsearch import IAdvSearchBackend

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
		
		return [
			{
				'name': 'TracHelp', 
				'score': 0.876, 
				'source': 'wiki', 
				'text': '==Trac Help== ....'
			},
		]

