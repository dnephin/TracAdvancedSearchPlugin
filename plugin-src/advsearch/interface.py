from trac.core import Interface 

class IAdvSearchBackend(Interface):
	"""Interface to provides a search service."""

	def get_name():
		"""Return the name of this backend."""

	def upsert_document(doc):
		"""
		Insert or update a document in the search backend.
		Accepts a dictionary doc which contains all the data about an updated
		document (wiki page, ticket, etc) to be inserted or updated in the 
		backend index. The keys of the dict should match the field names in
		the database.
		"""

	def delete_document(identifier):
		"""
		Remove a document from the search backend. Accepts a string identifer
		to uniquely identify the document in the index.  This should be in
		the form "<source>_<name>".
		"""


	def query_backend(criteria):
		"""
		Given a dictionary of criteria, perform a query in the search backend
		and return a list of dicts with the results. Backends should ignore any
		criteria it does not know how to deal with.

		Returns a tuple of (total result count, list of results).  Each results
		is a dict with keys: title, score, source, summary, date, author. 
		When multiple providers return results for a source score is used to 
		order the results. 

		Example:
		criteria = {
			'q': 'trac help',
			'author: ['admin', 'joe'],
			'source': ['wiki'],
			'date_start': '2011-04-01',
			'date_end': '2011-04-30',
		}

		return (
			200, 
			[
				{
					'title': 'TracHelp', 
					'score': 0.876, 
					'source': 'wiki', 
					'summary': '==Trac Help== ....'
					'date': '2011-02-34 23:34',
					'author': 'admin',
				},
				...
			]
		)
		"""


