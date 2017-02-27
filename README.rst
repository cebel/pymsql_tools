PyMySQL-tools
=============

:code:`PyMySQL-tools is a Python software package based on `pymysql` that allows to apply the most common
operation on a MySQL database.

Many standard operations like ''create, deleting or modify'' databases, table, columns, indices and many more
can easily be executed with this library. No SQL skills are needed.

.. code-block:: python

   >>> import pymysql_tools
   >>> pt = pymysql_tools.connect('host','user','passwd')

Examples
--------

.. code-block:: python

    >>> pt.databases()


''connect'' method from :code:`PyMySQL`. Please go to http://pymysql.readthedocs.io/en/latest/modules/connections.html
to get all possible parameters.

Installation
------------

PyMySQL-tools can be installed easily from Github with:

.. code-block:: sh

   pip3 install https://github.com/cebel/pymsql_tools.git

Links
-----

- PyMySQL: https://pypi.python.org/pypi/PyMySQL
