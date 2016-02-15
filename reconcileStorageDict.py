import difflib
import re
import string

class ReconcileStorageDict:
    """ Default storage/retrieval engine - holds the data as key:value dictionaries
    """

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
        """ Search for a query string in the dictionary
        """
    
        query_string = self.normalise_name(q.query)
        results = []
        matches = []
        
        # check for exact matches
        if( query_string in self.docs ):
            r = ReconcileHit( self.docs[query_string], 100 )
            results.append( r )
            matches.append( self.docs[query_string] ) 
        
        # otherwise iterate through all the docs and return anything containing the query
        for i in self.docs:
            if query_string in i and self.docs[i] not in matches:
                score = difflib.SequenceMatcher(None, query_string, i)
                score = (score.ratio() * 100)
                r = ReconcileHit( self.docs[i], score )
                results.append( r )
        
        return results
        
    def all(self):
        """ return all the values
        """
        return list(self.docs)
        
    def __getattr__(self, name):
        for i in self.docs:
            if( self.docs[i][self.id_field]==name ):
                return self.docs[i]
        
        raise AttributeError("ReconcileStorageDict instance has no attribute '%s'" % name)
    
    def normalise_name(self, str, options={}):
        """ Produce a normalised string from a given string, to remove
            the influence of lower/upper-case etc on matching
        """
    

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
    """ Class holding a possible reconciliation result
    """
    
    def __init__(self, result, score=100):
        self.result = result
        self.score = round( score, 2)
        
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