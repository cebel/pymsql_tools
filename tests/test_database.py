# -*- coding: utf-8 -*-

import unittest
import pymysql_tools

host = 'localhost'
user = 'test_user_pymysql_tools'
passwd = 'testpasswd'
database = 'test_pymysql_tools'


class TestDatabases(unittest.TestCase):

    def setUp(self):
        self.pt = pymysql_tools.connect(host, user, passwd, database)

    def test_database(self):
        self.pt = pymysql_tools.connect(host, user, passwd, database)
        self.assertEqual(self.pt.get_database_name(), database)
