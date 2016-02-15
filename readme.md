python-reconcile-csv
====================

Reconciliation engine for CSV files, for use with services like [OpenRefine](http://openrefine.org/). Concept based on the OKFN [reconcile-csv](http://okfnlabs.org/reconcile-csv/) project, but implemented in python rather than java.

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
		
3. Open your web browser to <http://localhost:8080/> to see the service specification. You can add this as a reconciliation service in OpenRefine.

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
  
  [default="id"] ID field in the CSV file. Can be a string column name or int column position.
  
- `-t`, `--type`
  
  [default="/item"] Type of object returned by the reconciliation service
  
- `-s`, `--search_field`
  
  [default="name"] Field in the CSV file which will be used. Can be a string column name or int column position.
  
- `--storage`
  
  [default="dict"] Which type of storage to use
  
- `--debug`
  
  Debug mode (autoreloads the server)