from reconcileStorageDict import *

class ReconcileEngine:
    """Main engine for powering the reconciliation
    
    Wraps around the search itself and controls the dict that is returned (and the server then
    converts into a JSON response)
    
    Search storage can be specified with the `storage` parameter
    """

    def __init__(self, source=None, id_field="id", search_field="name", type="match", service_url="http://localhost:8000/", storage=None, name="CSV Reconciliation Service"):
        """Initiate the ReconcileEngine. source is a list of dictionaries/lists
        """
        default_storage = ReconcileStorageDict
        if storage is None:
            storage = default_storage
        
        # the field the will be searched by default
        self.search_field = search_field
        # the field that will be used to index
        self.id_field = id_field
        # the name of the type of item being reconciled
        self.type = type
        # the url of the service
        self.url = service_url
        # the name of the reconciliation
        self.name = name
            
        # setup the storage
        self.storage = storage(source, search_field, id_field)
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.storage.close()
        
    def service_spec(self):
        """Return the default service specification
        
        Specification found here: https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Service-API#service-metadata
        """
        service_url = self.url
        return {
            "name": self.name,
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
        """Use the suggest API
        
        Currently doesn't work
        """
    
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
        """Fetch a user query from the storage and return in the correct format
        """
    
        # create a query and get the results from the storage engine
        q = ReconcileQuery(q)
        results = self.storage.search(q)
        
        # sort the results by score
        if getattr(results, "sort", None):
            results.sort(key=lambda x: x.score, reverse=True)
        
        # if there's a limit on results only return those results
        if q.limit:
            results = results[0:q.limit]
            
        # prepare each result in the JSON return format
        for i in results:
            
            # check if it's an exact match
            match = q.query.lower()==i[self.search_field].lower() or i.score==100
        
            q.add_result({
                "id":i[self.id_field],
                "name":i[self.search_field],
                "type":[{
                    "id": "/" + self.type,
                    "name": self.type
                }],
                "score":i.score,
                "match":match,
            })
            
            # if we've got an exact match then just return it
            if match:
                return q.results
        
        return q.results
        
    def queries(self, qs):
        """Allow multiple queries to be returned
        """
        
        qs = ReconcileQueries(qs)
        for k,q in qs.queries.iteritems():
            qs.add_result(k, self.query(q))
        return qs.results
        
    def view(self, id):
        """ Not yet implemented - should return a nice HTML view of the result
        """
        return getattr(self, id)
        
    def __getattr__(self, name):
        if(name=="source" or name=="data"):
            return self.storage.all()
    
        results = self.storage.__getattr__(name)
        
        if(len(results)>0):
            return results
        else:
            raise AttributeError("ReconcileEngine instance has no attribute '%s'" % name)

class ReconcileQuery:
    """
    Construct a query based on data provided by the user
    
    Can either take a string, or a dictionary with various properties
    """
    
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
        """ Add a result to the list of results
        """
    
        if(self.limit and self.limit<len(self.results["result"])):
            return
        self.results["result"].append(r)
        
class ReconcileQueries:
    """ Holds multiple queries
    """

    def __init__(self,qs):
        self.results = {}
        self.queries = qs
    
    def add_result(self, k, q):
        self.results[k] = q