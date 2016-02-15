import bottle

from reconcileEngine import *
from reconcileStorageWhoosh import *

import json
import argparse
import csv
from collections import OrderedDict

def get_from_csv(csv_file, header_row=True, delimiter=","):
    """ Turn a CSV file into a list of dicts/lists
    """

    source = []
    
    with open(csv_file, 'r') as f:
        if(header_row):
            reader = csv.DictReader(f, delimiter=delimiter)
        else:
            reader = csv.reader(f, delimiter=delimiter)
            
        for row in reader:
            source.append(row)
    
    return source         
            
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
    parser.add_argument('--name', default="CSV Reconciliation Service", help='Name of the reconciliation service')
    parser.set_defaults(header_row=True, debug=False)

    args = parser.parse_args()

    # URL that will host the reconciliation service
    service_url = "http://" + args.host + ":" + str(args.port) + "/"
    if args.debug: 
        print "Reconciliation service starting on:", service_url
    
    # get the data from the CSV file
    source = get_from_csv( args.csv, header_row = args.header_row, delimiter = args.delimiter )
    
    storage = None
    if(args.storage=="whoosh"):
        storage = ReconcileStorageWhoosh
    
    # Start the reconciliation engine and the bottle service
    with ReconcileEngine(source=source, 
        id_field=args.id_field, 
        search_field=args.search_field, 
        service_url = service_url,
        storage = storage,
        name = args.name,
        ) as r:
        
        @bottle.get('/')
        @bottle.post('/')
        def index():
            """ Index of the server. If ?query or ?queries used then search,
                otherwise return the default response as JSON
            """
            
            query = bottle.request.params.query or None
            
            # try fetching the query as json data or a string
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
                
            # if we're doing a callback request then do that
            if(bottle.request.query.callback):
                bottle.response.content_type = "application/javascript"
                return "%s(%s)" % (bottle.request.query.callback, r.service_spec())
                
            # otherwise just return the service specification
            return r.service_spec()
        
        @bottle.route('/view/<id>')
        def view(id):
            """ a view of a particular item - should be an HTML page
            """
            return bottle.template('result.html', 
                result=r.view( id ),
                id_field=args.id_field
                )
        
        @bottle.route('/suggest')
        def suggest():
            """ suggest API, not sure if this works
            """
            prefix = bottle.request.query.prefix or None
            if(prefix):
                return r.suggest({"prefix":prefix})
        
        @bottle.route('/data.html')
        @bottle.route('/all.html')
        def data():
            """ return all records
                @todo paginate for long records
            """
            docs = r.source
            headers = r.source[0].keys()
            
            return bottle.template('results.html', 
                result=docs,
                id_field=args.id_field,
                headings= headers,
                page_title=args.name
                )
        
        @bottle.route('/data')
        @bottle.route('/all')
        def data():
            """ return all records
                @todo paginate for long records
            """
            bottle.response.content_type = "application/json"
            return json.dumps(r.source)
        
        @bottle.route('/static/<filename:path>')
        def send_static(filename):
            """ if we need static files
            """
            return bottle.static_file(filename, root='./static')

        bottle.run(host=args.host, port=args.port, reloader=args.debug)        
        

if __name__ == '__main__':
    main()