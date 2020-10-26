python-reconcile-csv
====================

**UPDATE**

This repository has not been updated for python 3. An alternative could be to convert your 
CSV file to an sqlite table using [csvs-to-sqlite](https://github.com/simonw/csvs-to-sqlite) and 
then use [datasette](https://docs.datasette.io/en/stable/) and the [datasette-reconcile](https://github.com/drkane/datasette-reconcile/)
plugin to serve a Reconciliation Service API.

-------

Reconciliation engine for CSV files, for use with services like [OpenRefine](http://openrefine.org/). 
Concept based on the OKFN [reconcile-csv](http://okfnlabs.org/reconcile-csv/) project, 
but implemented in python rather than java.

Requirements
------------

### [Whoosh](https://pypi.python.org/pypi/Whoosh/)

Python indexing and text searching library

### [Bottle](http://bottlepy.org/docs/dev/index.html)

Micro web-framework for running the local server

Usage
-----

1. Download and unpack the repository

2. Run the following command:
		
		python reconcile.py /path/to/csv/file.csv
		
3. Open your web browser to <http://localhost:8080/> to see the service specification. 
   You can add this as a reconciliation service in OpenRefine.

4. Visit <http://localhost:8080/?query=example%20query> to see an example query. 

By default the reconciliation service uses a simple python dictionary to look up the 
results - the names are normalised and stored as keys, and the ids are returned based
on normalising the query.

To use the "whoosh" library, with more advanced indexing and fuzzy matching, then set
the `--storage` value to `whoosh` like so:

	python reconcile.py --storage whoosh /path/to/csv/file.csv

The server also allows you to view an individual record at <http://localhost:8080/view/ITEMID>
or view all the records at <http://localhost:8080/data.html>.
		
Command line arguments
----------------------

- `-d` `--delimiter`	

  [default=","] Delimiter for the CSV file
  
- `--no-header-row`	
  
  CSV file does not have a header row
  
- `-host`, `--host`	
  
  [default="localhost"] host for the service
  
- `-p`, `--port`
  
  [default=8080] port for the service

- `-id`, `--id_field`
  
  [default="id"] ID field in the CSV file. Can be a string column name or int column 
  position.
  
- `-t`, `--type`
  
  [default="/item"] Type of object returned by the reconciliation service
  
- `-s`, `--search_field`
  
  [default="name"] Field in the CSV file which will be used. Can be a string column 
  name or int column position.
  
- `--storage`
  
  [default="dict"] Which type of storage to use
  
- `--debug`
  
  Debug mode (autoreloads the server)
  
- `--name`

  [default="CSV Reconciliation Service"] Name of the reconciliation service