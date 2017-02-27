"""

PyMySQL-tools is tested on both Python3 and legacy Python2 installations on Mac OS and Linux.
.. warning:: PyBEL is not thoroughly tested on Windows.

Installation
------------

Easiest
~~~~~~~

.. code-block:: sh

   $ pip3 install pymysql_tools

Get the Latest
~~~~~~~~~~~~~~~

.. code-block:: sh

   $ pip3 install git+https://github.com/cebel/pymsql_tools.git

For Developers
~~~~~~~~~~~~~~

.. code-block:: sh

   $ git clone https://github.com/cebel/pymsql_tools.git
   $ cd pymysql_tools
   $ pip3 install -e .


Caveats
-------

- PyMySQL-tools extends the :code:`pymsql` for its core functionalities. 

"""

from .db import MySQLTools

__all__ = []

__version__ = '0.0.2'

__title__ = 'PyMySQL-tools'
__description__ = 'Basic '
__url__ = 'https://github.com/cebel/pymysql_tools'

__author__ = 'Christian Ebeling'
__email__ = 'christian.ebeling@scai.fraunhofer.de'

__license__ = 'Apache 2.0 License'
__copyright__ = 'Copyright (c) 2017 Christian Ebeling'


def connect( *args, **kwargs):
    return MySQLTools(*args, **kwargs)