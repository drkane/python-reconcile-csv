import whoosh.index
import whoosh.fields
import whoosh.qparser

from reconcileStorageDict import *

import shutil
import tempfile
            
class ReconcileStorageWhoosh( ReconcileStorageDict ):
    """ Storage/retrieval engine using the Whoosh library
    """

    def __init__(self, source, search_field, id_field):
    
        # the temporary directory the index will be located in
        self.index_dir = tempfile.mkdtemp()
        # the field the will be searched by default
        self.search_field = search_field
        # the field that will be used to index
        self.id_field = id_field
        
        # create a schema and index
        schema = whoosh.fields.Schema()
        self.ix = whoosh.index.create_in(self.index_dir, schema)
        
        # populate the schema with fields from the first row of the source
        self.writer = self.ix.writer()
        for field in source[0]:
            if( self.id_field == field ):
                self.writer.add_field( field, whoosh.fields.ID(stored=True))
            else:
                self.writer.add_field( field, whoosh.fields.TEXT(stored=True))
                
            if(self.search_field==None and field != self.id_field):
                self.search_field = field
        
        # add documents to index
        for i in source:
            i2 = {}
            for k,v in i.items():
                if( isinstance(v, str)):
                    i2[k] = unicode(v)
                else:
                    i2[k] = v
            self.writer.add_document(**i2)
        self.writer.commit()
        
        self.searcher = self.ix.searcher()
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type="", exc_value="", traceback=""):
        self.searcher.close()
        self.ix.close()
        shutil.rmtree(self.index_dir)
        
    def close(self):
        self.__exit__()
    
    def search(self, q):
        query = whoosh.qparser.QueryParser(self.search_field, self.ix.schema, termclass=whoosh.query.Variations).parse(q.query)
        results = self.searcher.search(query)
        return list(results)
        
    def all(self):
        docs = self.searcher.documents()
        data = []
        for d in docs:
            data.append(d)
        return data
        
    def __getattr__(self, name):
        parser = whoosh.qparser.QueryParser(self.id_field, self.ix.schema)
        parser.add_plugin(whoosh.qparser.FuzzyTermPlugin())
        query = parser.parse(name)
        results = self.searcher.search(query)
        if(len(results)>0):
            return results[0].fields()
        else:
            raise AttributeError("ReconcileStorageWhoosh instance has no attribute '%s'" % name)