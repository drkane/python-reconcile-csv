import whoosh.index
import whoosh.fields
import whoosh.qparser
import bottle

import shutil
import tempfile
import json
import argparse
import csv
from collections import OrderedDict

class ReconcileEngine:

    def __init__(self, source=None, source_csv=None, id_field="id", search_field="name", type="match", service_url="http://localhost:8000/", header_row=True, delimiter=",", storage='dict'):
        
        # the field the will be searched by default
        self.search_field = search_field
        # the field that will be used to index
        self.id_field = id_field
        # the name of the type of item being reconciled
        self.type = type
        # the url of the service
        self.url = service_url
        
        # get data from a CSV file if needed
        if(source==None and source_csv!=None):
            source = self.get_from_csv(source_csv, header_row, delimiter)
            
        # setup the storage
        if(storage=="whoosh"):
            self.storage = ReconcileStorageWhoosh(source, search_field, id_field)
        else:
            self.storage = ReconcileStorageDict(source, search_field, id_field)
        
        
    def get_from_csv(self, csv_file, header_row=True, delimiter=","):

        source = []
        
        with open(csv_file, 'r') as f:
            if(header_row):
                reader = csv.DictReader(f, delimiter=delimiter)
            else:
                reader = csv.reader(f, delimiter=delimiter)
                
            for row in reader:
                source.append(row)
        
        return source
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.storage.close()
        
    def service_spec(self):
        service_url = self.url
        return {
            "name": "CSV Reconciliation Service",
            "identifierSpace": "http://rdf.freebase.com/ns/type.object.id",
            "schemaSpace": "http://rdf.freebase.com/ns/type.object.id",
            "view": {
                "url": service_url + "view/{{id}}"
            },
            "preview" : {
                "url": service_url + "preview/{{id}}",
                "width": 430,
                "height": 300
            },
            "suggest" : {
                "entity" : {
                    "service_url": service_url,
                    "service_path": "/suggest",
                    "flyout_service_url": service_url,
                    "flyout_service_path": "/flyout"
                }
            },
            "defaultTypes" : [{
                "id": "/" + self.type,
                "name": self.type
            }]
        }
        
    def suggest(self, q):
    
        prefix = q["prefix"]
        q["query"] = q["prefix"] + "*"
        q = self.query(q)
        
        return {
            "code": "/api/status/ok",
            "status": "200 OK",
            "prefix": prefix,
            "result": q["result"],
        }
        
    def query(self, q):
    
        q = ReconcileQuery(q)
        results = self.storage.search(q)
        
        if q.limit:
            results = results[0:q.limit]
            
        for i in results:
            q.add_result({
                "id":i[self.id_field],
                "name":i[self.search_field],
                "type":[{
                    "id": "/" + self.type,
                    "name": self.type
                }],
                "score":i.score,
                "match":q.query.lower()==i[self.search_field].lower(),
            })
        
        return q.results
        
    def queries(self, qs):
        
        qs = ReconcileQueries(qs)
        for k,q in qs.queries.iteritems():
            qs.add_result(k, self.query(q))
        return qs.results
        
    def view(self, id):
        return getattr(self, id)
        
    def __getattr__(self, name):
        if(name=="source" or name=="data"):
            return self.storage.all()
    
        results = self.storage.__getattr__(name)
        if(len(results)>0):
            return results[0].fields()
        else:
            raise AttributeError("ReconcileEngine instance has no attribute '%s'" % name)

class ReconcileQuery:

    def __init__(self, q):
        defaults = {
            "query":"",
            "limit":None,
            "type":None,
            "type_strict":None,
            "properties":[],
        }
    
        # if the query is a string then construct an object
        if( isinstance( q, basestring ) ):
            q = {"query":q}
            
        # get the values, using defaults if needed
        for a in defaults:
            if(a in q):
                setattr(self, a, q[a])
            else:
                setattr(self, a, defaults[a])
                
        # initialise the results array
        self.results = {"result":[]}
        
    def add_result(self, r):
        if(self.limit and self.limit<len(self.results["result"])):
            return
        self.results["result"].append(r)
        
class ReconcileQueries:

    def __init__(self,qs):
        self.results = {}
        self.queries = qs
    
    def add_result(self, k, q):
        self.results[k] = q
            
class ReconcileStorageWhoosh:

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

    def __exit__(self, exc_type, exc_value, traceback):
        self.searcher.close()
        self.ix.close()
        shutil.rmtree(self.index_dir)
        
    def close(self):
        self.__exit__()
    
    def search(self, q):
        query = whoosh.qparser.QueryParser(self.search_field, self.ix.schema, termclass=whoosh.query.Variations).parse(q.query)
        return self.searcher.search(query)
        
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
            
class ReconcileStorageDict:

    def __init__(self, source, search_field, id_field):
    
        # the field the will be searched by default
        self.search_field = search_field
        # the field that will be used to index
        self.id_field = id_field
        
        # create the dict
        self.docs = {}
        
        # add documents to index
        for i in source:
            key = i[self.search_field]
            key = self.normalise_name(key)
            self.docs[key] = i
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type="", exc_value="", traceback=""):
        self.docs = {}
        
    def close(self):
        self.__exit__()
    
    def search(self, q):
        query_string = self.normalise_name(q.query)
        results = []
        if( query_string in self.docs ):
            r = ReconcileHit( self.docs[query_string], 100 )
            results.append( r )
        return results
        
    def all(self):
        return self.docs
        
    def __getattr__(self, name):
        for i in self.docs:
            if( self.docs[i][self.id_field]==name ):
                return self.docs[i]
        
        raise AttributeError("ReconcileStorageDict instance has no attribute '%s'" % name)
    
    def normalise_name(self, str, options={}):
        import re, string

        default_options = {
            "reorder": False,       # if true then the words in the string are reordered into alphabetical order
            "remspaces": False,     # if true then all spaces between words are removed.
            "rembrackets": False,   # if true then any words within brackets are removed.
            "replacewords": True,   # if true then particular words are removed from the string.
            
            # an array of the words that will be removed from the string. Values in the array can either be a string, in which case the word will be removed from anywhere in str, or an array with attributes "name" (the word) and "type" (beginning|middle|end) specifying where the word will be removed.
            "words":[
                {"name":"the",      "type":"beginning"}, 
                {"name":"the",      "type":"end"},
            ]
        }

        # set default options where no option is set
        for key in default_options:
            if( key not in options):
                options[key] = default_options[key]
                
        str = str.lower()                           # make the string lowercase
        str = str.replace("&"," and ")              # replace any ampersands with " and "
        
        # if we've chosen to remove brackets
        if(options["rembrackets"]):
            preg_brackets = r'\([^)]*\)'            # regex expression for brackets
            str = re.sub( preg_brackets, "", str)   # replace any text in the brackets
        
        str = str.replace("'","")                   # replace any apostrophes
        preg_nonalpha = r'[^a-zA-Z0-9 ]'            # regex expression for non-alphabetic characters
        str = re.sub( preg_nonalpha, "", str)       # replace any non-alphanumeric characters with a space
        
        # if we've chosen to replace specific words in the string
        if( options["replacewords"] ):
            # for each word, remove it from end, beginning or middle as specified
            for w in options["words"]:
                if( isinstance(w, basestring) ):
                    w = {"type":"middle", "name":w}
                if( w["type"]=="end" ):
                    if( str.endswith( w["name"] ) ):
                        str = str[:-len( w["name"] )]
                elif( w["type"]=="middle" ):
                    str = str.replace( w["name"]," ")
                else:
                    if( str.startswith( w["name"] ) ):
                        str = str[len( w["name"] ):]
        
        str = str.strip()                           # trim to remove any trailing spaces left over from the word removal
        str = re.sub( r'\s+', " ", str)             # remove any double spaces
        
        # if we're reordering the string
        if( options["reorder"] ):
            str_array = str.split()                 # create an array with all the words in the string in it
            str_array = sorted(str_array)           # sort the array alphabetically
            str = string.join(str_array)            # put the words back together again
        
        # remove all spaces from the string
        if( options["remspaces"]):
            str = str.replace( " ","")
        
        return str                                  # return the normalised string

class ReconcileHit:
    
    def __init__(self, result, score=100):
        self.result = result
        self.score = 100
        
    def fields(self):
        return self.result
        
    def __getattr__(self, name):
        if name in self.result:
            return self.result[name]
            
        raise AttributeError("ReconcileHit instance has no attribute '%s'" % name)
        
    def __getitem__(self, name):
        if name in self.result:
            return self.result[name]
            
        raise AttributeError("ReconcileHit instance has no attribute '%s'" % name)
            
            
def main():

    parser = argparse.ArgumentParser(description='Run a reconciliation service based on a CSV file')
    parser.add_argument('csv', help='path to a CSV file which will be reconciled against')
    parser.add_argument('-d', '--delimiter', default=",", help='Delimiter for the CSV file')
    parser.add_argument('--no-header-row', action='store_false', dest="header_row", help='CSV file does not have a header row')
    parser.add_argument('-host', '--host', default="localhost", help='host for the service')
    parser.add_argument('-p', '--port', default=8080, help='port for the service')
    parser.add_argument('-id', '--id_field', default="id", help='ID field in the CSV file')
    parser.add_argument('-t', '--type', default="/item", help='Type of object returned by the reconciliation service')
    parser.add_argument('-s', '--search_field', default="name", help='Field in the CSV file which will be used')
    parser.add_argument('--storage', default="dict", help='Which type of storage to use')
    parser.add_argument('--debug', action='store_true', dest="debug", help='Debug mode (autoreloads the server)')
    parser.set_defaults(header_row=True, debug=False)

    args = parser.parse_args()

    service_url = "http://" + args.host + ":" + str(args.port) + "/"
    if args.debug: print "Reconciliation service starting on:", service_url
    
    with ReconcileEngine(source_csv=args.csv, 
        id_field=args.id_field, 
        search_field=args.search_field, 
        service_url = service_url,
        header_row = args.header_row,
        delimiter = args.delimiter,
        storage = args.storage
        ) as r:
        
        @bottle.get('/')
        @bottle.post('/')
        def index():
            
            query = bottle.request.params.query or None
            
            if query:
                try:
                    query = json.loads(query)
                except ValueError:
                    query = query
                return r.query(query)
                
            queries = bottle.request.params.queries or None
            
            if queries:
                queries = json.loads(queries, object_pairs_hook=OrderedDict)
                return r.queries(queries)
                
            if(bottle.request.query.callback):
                bottle.response.content_type = "application/javascript"
                return "%s(%s)" % (bottle.request.query.callback, r.service_spec())
                
            return r.service_spec()
        
        @bottle.route('/view/<id>')
        def view(id):
            return getattr(r,id)
        
        @bottle.route('/suggest')
        def suggest():
            prefix = bottle.request.query.prefix or None
            if(prefix):
                return r.suggest({"prefix":prefix})
        
        @bottle.route('/data')
        def data():
            bottle.response.content_type = "application/json"
            return json.dumps(r.source)

        bottle.run(host=args.host, port=args.port, reloader=args.debug)        
        

if __name__ == '__main__':
    main()