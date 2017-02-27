#!/usr/bin/env python
"""
Library for MySQL actions
@author: Christian Ebeling
@contact: chr.ebeling@gmail.com
@version: 0.0.1 (03-01-2017)
the order of the arguments in this library should follow the pattern
methode_name_seperated_by_(cursor,table,column,other_arguments)"""

import re
import string
import pymysql
import pickle
import datetime
import os
import sys

from time import gmtime, strftime

class MySQLTools:

    def __init__(self, *args, **kwargs):
        self.conn = pymysql.Connection(*args, **kwargs)
        self.cursor = self.conn.cursor()
        self.cursor_dict = self.conn.cursor(pymysql.cursors.DictCursor)

    def update_empty_string_to_null(self, table, columns=[]):
        """updates empty string to NULL (if allowed) for all columns (default=[]=>all columns in table)
        column_list could also a string if only one column have to be updated
        returns a dictionary of the updated columns in the form {'name_of_column':number_of_updates,...}
        :param table: Table name
        :param columns: column names
        :param cursor: pymysql cursor         
        """
        columns_updated = {}
        columns = self.__get_columns(table, columns)
        for column in columns:
            if self.get_column_information_schema(table, column)['IS_NULLABLE'] == "YES":
                columns_updated[column] = self.cursor.execute(
                    "update `%s` set `%s` = NULL where trim(`%s`)=''" % (table, column, column))
        return columns_updated

    def get_hostname(self):
        """return the hostname"""
        self.cursor.execute("SELECT @@hostname")
        return self.cursor.fetchone()[0]

    def get_user(self):
        """return the user"""
        self.cursor.execute("SELECT SUBSTRING_INDEX(USER(),'@',1)")
        return self.cursor.fetchone()[0]

    def get_columns_with_null(self, table):
        """get all column names with NULL
        :param table: table name
        :type table: str
        """
        self.cursor.execute("describe " + table)
        return [x[0] for x in self.cursor.fetchall() if x[2] == 'YES']

    def rename_table(self, old_table_name, new_table_name):
        """renames a table
        :param old_table_name: old table name
        :type old_table_name: str
        :param new_table_name: new table name
        :type new_table_name: str
        """
        return self.cursor.execute("rename table `%s` to `%s`" % (old_table_name, new_table_name))

    def trim_all(self, table, columns=[]):
        """
        :param table: table name
        :type table: str
        :param columns: column name(s)
        :type columns: iterable of str or str
        """
        columns = self.__get_columns(table, columns)
        for column in columns:
            if self.get_column_information_schema(table, column)['DATA_TYPE'] in ('text', 'varchar', 'char', 'blob'):
                self.cursor.execute("update `%s` set `%s`=trim(trim(TRAILING '\r\n' FROM `%s`))"
                                    % (table, column, column))

    def change_columns_to_not_null(self, table, columns=[]):
        """change a column to 'NOT NULL' if all rows are filled (not NULL), returns a list of changed columns
        :param table: table name
        :type table: str
        :param columns: column name(s) 
        :type columns: iterable o str or str
        """
        columns_changed = []
        columns = self.__get_columns(self.cursor, table, columns)
        for column in columns:
            if not self.cursor.execute("SELECT * from `%s` where `%s` IS NULL" % (table, column)):
                col_info = self.get_column_information_schema(self.cursor, table, column)
                char_set_name = col_info['CHARACTER_SET_NAME']
                character_set = " CHARACTER SET " + char_set_name if char_set_name else ''
                coll_name = col_info['COLLATION_NAME']
                collate = " COLLATE " + coll_name if coll_name else ''
                self.cursor.execute("ALTER TABLE `%s` CHANGE `%s` `%s` %s %s %s NOT NULL"
                                    % (table, column, column, col_info['COLUMN_TYPE'], character_set, collate))
        return columns_changed

    def __get_columns(self, table, columns):
        """get all columns
        :param table: table name
        :type table: str
        :param columns: column name(s) 
        :type columns: iterable o str or str        
        """
        if type(columns) == str:
            columns = [columns]
        elif type(columns) in [list, tuple] and len(columns) == 0:
            columns = self.get_column_names(table)
        return columns

    def add_primary_key(self, table, name_of_column='id'):
        """add a column with the name 'id' (default to the table in the first position)
        if a column with the name id already exists program will exit
        :param table: table name
        :type table: str
        :param name_of_column: name of promary key column
        :type name_of_column: str
        """
        self.cursor.execute("ALTER TABLE %s ADD COLUMN %s INT NOT NULL AUTO_INCREMENT FIRST, ADD primary KEY id(%s)"
                            % (table, name_of_column, name_of_column))

    def use_database(self, database):
        """change database
        :param database: database name
        :type database: str
        """
        self.cursor.execute("use " + database)

    def database_exists(self, database_name):
        """
        check if database exists
        :param database_name: database name
        :type database_name: str
        """
        database_list = [db.lower() for db in self.get_database_names()]
        if database_name in database_list:
            return True
        else:
            return False

    def drop_all_indices(self, database, table):
        """Drop all indice for speicfic table if exists
        Except Primary key
        :param database: database name
        :type database: str
        :param table: table name
        :type table: str
        """
        self.cursor.execute("SHOW INDEX FROM %s.%s" % (database, table))
        index_list = set()  # rip duplicate index name which happens on composite index
        for result in self.cursor.fetchall():
            index = result[2]
            if index.lower() != 'primary':  # not drop primary key
                index_list.add(index)
        for index in index_list:
            self.cursor.execute("DROP INDEX %s ON %s.%s " % (index, database, table))

    def drop_create_database(self, database):
        """Drops the database dbname if exists, creates a new database dbname and finally 
        connects the cursor to dbname"""
        self.cursor.execute("drop database if exists %s" % database)
        self.cursor.execute("create database %s" % database)
        self.use_database(database)

    def add_column(self, table, column, column_description):
        """add column(s) to table. Schema of columns for one e.g..: ('column_name','int(10) NOT NULL') for multiple (('cn1','col_desc'),('cn1','col_desc'),...)'"""
        # TODO: fix this methode
        if column not in self.get_column_names(cursor, table):
            self.cursor.execute("ALTER TABLE `%s` ADD `%s` %s" % (table, column, column_description))
        else:
            print("column `%s` in table `%s` already exists" % (column, table))
            return 0
        return 1

    def create_unique_index(self, table, index_name, over_columns=[]):
        """creates unique index (or indices) on table.column(s)"""
        if type(over_columns) == str:
            over_columns = [over_columns]
        self.cursor.execute("describe " + table)
        field_keys = [(x[0], x[3]) for x in self.cursor.fetchall()]
        if (index_name, 'UNI') not in field_keys:
            if len(over_columns):
                self.cursor.execute("alter table `" + table + "` add unique " + index_name + " (" + (
                ",".join(["`" + x + "`" for x in over_columns])) + ")")
            else:
                self.cursor.execute("ALTER TABLE `" + table + "` ADD UNIQUE (`" + index_name + "`)")
            return True
        else:
            return False

    def create_database(self, database):
        self.cursor.execute("create database `" + database + "`")

    def create_index(self, table, columns):
        """creates  1 index per column if data type is varchar, char, int"""
        if type(columns) == str:
            columns = [columns]

        for column in columns:
            if self.column_exists(table, column):
                Field, Type, Null, Key, Default, Extra = self.cursor.fetchone()
                if Key:  # and not quiet?
                    print(table + "." + Field + " already have a " + Key + " key index")
                    continue
                else:
                    if Type not in ["text", "longtext"]:
                        self.cursor.execute("ALTER TABLE " + table + " ADD INDEX ( `" + column + "` )")
                    else:
                        try:
                            sql = "ALTER TABLE " + table + " ADD FULLTEXT (`" + column + "`)"
                            self.cursor.execute(sql)
                        except:
                            print("Not possible to execute following SQL:", sql)
            else:
                print(
                    "########### ALERT##############:\n Not able to create index on column " + table + "." + column + " because " + column + " not exists\n\n")

    def index_on_cols_ends_with(self, tables, column_ends_with):
        print("Create index on all columns in tables ends with ", column_ends_with)
        if type(tables) == str:
            tables = [tables]
        for table in tables:
            for Field, Type, Null, Key, Default, Extra in self.get_column_names(table):
                if Field.endswith(column_ends_with) and not Key:
                    try:
                        print("Create index on " + table + "." + Field)
                        sql = "ALTER TABLE `" + table + "` ADD INDEX (`" + Field + "`)"
                        self.cursor.execute(sql)
                    except:
                        print("Not possible to execute following SQL:", sql)

    def table_unique(self, tables=None):
        """make table(s) (string = 1 table, list = many tables or None = all) unique"""
        print("make table(s) unique")
        if type(tables) == str:
            tables = [tables]
        elif len(tables) == 0:
            tables = self.get_table_names()
        columns = self.get_column_names(tables)
        for table, columns in columns.items():
            if self.get_primary_key(table):
                print("\ttable %s already unique because primary key exists" % (table))
                continue
            count_distinct = self.cursor.execute("SELECT distinct * from `%s`" % (table))
            self.cursor.execute("SELECT count(*) from `%s`" % (table))
            count_all = self.cursor.fetchone()[0]
            diff = count_all - count_distinct
            if diff:
                print("\tmake table " + table + " unique")
                self.cursor.execute("show create table `%s`" % table)
                create_table = self.cursor.fetchone()[1]
                self.cursor.execute("Alter table `%s` rename `temp_%s`" % (table, table))
                self.cursor.execute(create_table)
                self.cursor.execute("insert into `%s` SELECT distinct * from `temp_%s`" % (table, table))
                self.cursor.execute("Drop table `temp_%s`" % table)
            else:
                print("table %s already unique" % table)

    def drop_columns(self, table, column_list):
        """drop columns in table, column_list could be a list of string or just a string for one column"""
        if type(column_list) == str:
            column_list = [column_list]
        for column in column_list:
            self.cursor.execute("ALTER TABLE `%s` DROP `%s`" % (table, column))

    def column_exists(self, table, column):
        return self.table_exists(table) and self.cursor.execute("show columns from `%s` like '%s'" % (table, column))

    def drop_tables(self, tables):
        """Drop tables(tuple or list of strings) if exists
        :param tables: tuple or list of table names
        @return: list of dropped table names
        """
        droppedTables = []
        for table in tables:
            if self.drop_table(table):
                droppedTables += [table]
        return droppedTables

    def drop_table(self, table):
        """Drop table if exists
        :param table: table name to remove 
        @return: True if remove else False
        """
        if self.table_exists(table):
            self.cursor.execute("drop table `%s`" % table)
            removed = True
        else:
            removed = False
        return removed

    def analyse_table(self, table, database=None, **params):
        """analyse table and returns dict with columns names as keys and values is dictionary with following keys Field_name,Min_value,Max_value,Min_length,Max_length,Empties_or_zeros,Nulls,Avg_value_or_avg_length,Std,Optimal_fieldtype
        :param table: Table name
        :param columns: Column name (string,list or tuple of strings)
        :param cursor: pymysql cursor  
        :param params: parameter set {'enums':['list','of','enum','column','names'],...}
        """
        if not database:
            database = self.get_database_name()
        columns = ['Min_value', 'Max_value', 'Min_length', 'Max_length', 'Empties_or_zeros', 'Nulls',
                   'Avg_value_or_avg_length', 'Std', 'Optimal_fieldtype']
        self.cursor.execute("SELECT * FROM `%s`.`%s` PROCEDURE ANALYSE ()" % (database, table))
        analyse_dict = {}
        for x in self.cursor.fetchall():
            column = x[0].split(".")[- 1]
            adict = dict(zip(columns, list(x[1:])))
            add_to_analyse_dict = True
            if adict['Optimal_fieldtype'].startswith('ENUM') and ('enums' not in params or column in params['enums']):
                if len(adict['Optimal_fieldtype'].split("','")) < 30 and max(
                        [len(x) for x in adict['Optimal_fieldtype'][5:-2].split("','")]) < 100:
                    # Optimal_fieldtype could be a long list of integers stored before as string
                    # the general suggestion from MySQL is an ENUM, more sense makes INT
                    onlyIntergers = re.search("^(ENUM\(('-?\d+(e\+\d{2})?'(,'-?\d+(e\+\d{2})?')+)\))",
                                              adict['Optimal_fieldtype'])
                    if onlyIntergers:
                        adict['Optimal_fieldtype'] = 'INT ' + adict['Optimal_fieldtype'][len(onlyIntergers.groups()[0]):]

                    # Optimal_fieldtype could be a long list of floats stored before as string
                    # the general suggestion from MySQL is an ENUM, more sense makes FLOAT
                    onlyFloats = re.search("^(ENUM\('-?\d+(\.\d+)?'(,'-?\d+(\.\d+)?')+\))", adict['Optimal_fieldtype'])
                    if onlyFloats and re.search("^ENUM\([^)]*'-?\d+\.\d+'[^)]*\)", adict['Optimal_fieldtype']):
                        adict['Optimal_fieldtype'] = 'FLOAT ' + adict['Optimal_fieldtype'][len(onlyFloats.groups()[0]):]

                    # Optimal_fieldtype could be a long list of 'date time' stored before as string
                    # the general suggestion from MySQL is an ENUM, more sense makes DATETIME
                    onlyDatetimes = re.search(
                        "^(ENUM\('[12]\d{3}-[01]\d-[0-3]\d +[012]\d:[0-5]\d:[0-5]\d.\d+'( *, *'[12]\d{3}-[01]\d-[0-3]\d +[012]\d:[0-5]\d:[0-5]\d.\d+')+\))",
                        adict['Optimal_fieldtype'])
                    if onlyDatetimes:
                        adict['Optimal_fieldtype'] = 'DATETIME ' + adict['Optimal_fieldtype'][
                                                                   len(onlyDatetimes.groups()[0]):]
                else:
                    add_to_analyse_dict = False

                    # Optimal_fieldtype could be a long list of date stored before as string
            # the general suggestion from MySQL is an ENUM, more sense makes DATE
            # TODO: check next 3 lines makes sense because it slows down the execution
            # foundSomethingElseThanDate = self.cursor.execute("SELECT * from %s where %s not regexp '^[12][0-9]{3}-[01][0-9]-[0-3][0-9]$'" % (table,column))
            # if not foundSomethingElseThanDate:
            #    adict['Optimal_fieldtype'] = 'DATE'

            # Because of Float problems restrictions of digits before and after dot are deleted
            if adict['Optimal_fieldtype'].startswith('FLOAT'):
                adict['Optimal_fieldtype'] = re.sub("\(\d+,\d+\)", "", adict['Optimal_fieldtype'])

            if add_to_analyse_dict:
                analyse_dict[column] = adict

        return analyse_dict

    def drop_indices(self, dbcursor, tables=[], delete_primary_unique=0):
        """Drop all indices in a table (as string) or tables (as list) except PRIMARY and UNIQUE"""
        if type(tables) == str:
            tables = [tables]
        elif len(tables) == 0:
            dbcursor.execute("Show tables")
            tables = [x[0] for x in dbcursor.fetchall()]
        droped_indices = []
        for table in tables:
            dbcursor.execute("describe " + table)
            deleted_indices = []
            for r in dbcursor.fetchall():
                if r[3] and ((delete_primary_unique == 0 and r[3] != "UNI" and r[3] != "PRI") or delete_primary_unique) and \
                                r[0] not in deleted_indices and r[5] != "auto_increment":
                    sql = "ALTER TABLE `%s` DROP INDEX `%s`" % (table, r[0])
                    try:
                        dbcursor.execute(sql)
                    except:
                        print(__file__, "\nCan't execute following SQL:\n", sql)
                    deleted_indices += [r[0]]
                    droped_indices += [r]
        return droped_indices

    def compare_database_structures(self, dbcursor1, dbcursor2, tablePrefix1='', tablePrefix2=''):
        """Compare the structure of two databases"""
        dbcursor1.execute("SELECT database()")
        db_name1 = dbcursor1.fetchone()[0]
        dbcursor2.execute("SELECT database()")
        db_name2 = dbcursor2.fetchone()[0]
        schema1 = self.get_db_schema(dbcursor1, tablePrefix1)
        schema2 = self.get_db_schema(dbcursor2, tablePrefix2)
        # print schema1,schema2
        return self.compare_database_schemas(schema1, schema2, db_name1, db_name2, tablePrefix1, tablePrefix2)

    def compare_database_schemas(self, dbCursor1, dbCursor2, tablePrefix1='', tablePrefix2=''):
        """Compare two schemas of independent database structures according to the pymysql cursor (with database)"""
        schema1 = self.get_db_schema(dbCursor1, tablePrefix1)
        schema2 = self.get_db_schema(dbCursor2, tablePrefix2)
        tables1 = set([(x[len(tablePrefix1):] if tablePrefix1 else x) for x in schema1.keys()])
        tables2 = set([(x[len(tablePrefix2):] if tablePrefix2 else x) for x in schema2.keys()])
        result = {
            'tablesIn1ButNotIn2': list(tables1 - tables2),
            'tablesIn2ButNotIn1': list(tables2 - tables1),
            'columnsIn1ButNotIn2': {},
            'columnsIn2ButNotIn1': {}
        }
        for table in tables1 & tables2:
            result['columnsIn1ButNotIn2'][table] = list(
                set(schema1[tablePrefix1 + table].keys()) - set(schema2[tablePrefix2 + table].keys()))
            result['columnsIn2ButNotIn1'][table] = list(
                set(schema2[tablePrefix2 + table].keys()) - set(schema1[tablePrefix1 + table].keys()))
        return result

    def check4double(self, tables=[]):
        """Check if tables in database have redundant entries"""
        redundant_tables = {}
        tables = self.__tables_or_not(self.cursor, tables)
        for table in tables:
            self.cursor.execute("describe " + table)
            fields = string.join(
                [desc[0] for desc in self.cursor.fetchall() if desc[0] != table + "_id" and desc[0] != "last_change"], ",")
            number_all = self.cursor.execute("SELECT " + fields + " from " + table)
            number_distinct = self.cursor.execute("SELECT distinct " + fields + " from " + table)
            if number_all != number_distinct:
                intervall = number_all - number_distinct
                redundant_tables[table] = intervall
        return redundant_tables

    def save_database_structure(self, dbcursor, file_location):
        schema = self.get_db_schema(dbcursor)
        folder, file = os.path.split(file_location)
        if os.path.isdir(folder):
            fd = open(file_location, "w")
            pickle.dump(schema, fd)
            return 1
        else:
            return 0

    def get_database_name(self):
        """Returns a databasename if the cursor is connect to database else empty string"""
        self.cursor.execute("SELECT database()")
        return self.cursor.fetchone()[0]

    def get_primary_key(self, table):
        """returns primary key column name"""
        self.cursor.execute("describe " + table)
        primary_key = [x[0] for x in self.cursor.fetchall() if x[3] == "PRI"]
        if len(primary_key) == 1:
            primary_key = primary_key[0]
        else:
            primary_key = None
        return primary_key

    def get_database_names(self):
        self.cursor.execute("show databases")
        return [x[0] for x in self.cursor.fetchall()]

    def get_db_schema(self, tablePrefix):
        schema = {}
        sqlExtention = (" like '%s%%'" % tablePrefix) if tablePrefix else ''
        self.cursor.execute("show tables" + sqlExtention)
        for table, in self.cursor.fetchall():
            self.cursor.execute("describe " + table)
            schema[table] = {}
            for Field, Type, Null, Key, Default, Extra in self.cursor.fetchall():
                schema[table][Field] = {"Type": Type, "Null": Null, "Key": Key, "Default": Default, "Extra": Extra}
        return schema

    def get_table_schema(self, table):
        schema = {}

        self.cursor.execute("describe " + table)

        for Field, Type, Null, Key, Default, Extra in self.cursor.fetchall():
            schema[Field] = {"Type": Type, "Null": Null, "Key": Key, "Default": Default, "Extra": Extra}
        return schema

    def compare_database_with_old_schema(self, dbcursor, pickle_file):
        """Compares an old pickle dumped database schema with the structure of the database"""
        fd = open(pickle_file)
        schema_old = pickle.load(fd)
        schema_new = self.get_db_schema(dbcursor)
        dbcursor.execute("SELECT database()")
        db_name = dbcursor.fetchone()[0]
        i = 0
        path = ""
        for dir in pickle_file.split("/"):
            i += 1
            path += " " * i
            path += "+- " + dir + "\n"
        out = "Compare old database schema (first) in file \n" + path + "\n (dumped with pickle) with new database '" + db_name + "'\n\n"
        out += self.compare_database_schemas(schema_old, schema_new, db_name, "saved database structure")
        return out

    def write_schema_dump_file(self, cursor, file_location='./', db_name=''):
        timestamp = strftime("%a_%d_%b_%Y_%H_%M_%S", gmtime())
        schema = self.get_db_schema(cursor)
        fd = open(file_location + db_name + timestamp + ".pickle", 'w')
        pickle.dump(schema, fd)

    def get_col_desc_sql(self, pymysql_describe_table_sql_query, position_in_tab=0):
        """returns a dictionary with properties of a colum (describe table x)\
        keys are: field,type,type_name,type_size,null,key,default,extra,position_in_tab
        """
        r = pymysql_describe_table_sql_query
        column = {"field": r[0], "type": r[1], "type_name": "", "type_size": 0, "null": r[2], "key": r[3], "default": "",
                  "extra": r[5], "position_in_tab": position_in_tab}
        column["type_name"] = r[1].split("(")[0]
        if column["type_name"] in ["varchar", "char", "int"]:
            column["type_size"] = int(re.search("\(([0-9]*)\)", r[1]).group(1))
        if r[4] is None:
            column["default"] = "DEFAULT NULL"
        else:
            column["default"] = "DEFAULT '" + r[4] + "'"
        if column["type"] == "longtext":
            column["type_size"] = 2 ** 32
        if column["type"] == "text":
            column["type_size"] = 2 ** 16
        return column

    def get_column_information_schema(self, table, column):
        """
        function which returns information_schema.COLUMNS as dictionary for one column
        :param table: Table name
        :param column: Column name
        :param cursor: pymysql cursor     
        format of return dictionary {'Column_name_from_information_schema':value,...}
        keys:
            TABLE_CATALOG
            TABLE_SCHEMA
            TABLE_NAME           
            COLUMN_NAME
            ORDINAL_POSITION
            COLUMN_DEFAULT
            IS_NULLABLE
            DATA_TYPE
            CHARACTER_MAXIMUM_LENGTH
            CHARACTER_OCTET_LENGTH
            NUMERIC_PRECISION
            NUMERIC_SCALE
            CHARACTER_SET_NAME
            COLLATION_NAME
            COLUMN_TYPE
            COLUMN_KEY
            EXTRA
            PRIVILEGES
            COLUMN_COMMENT
        """
        information_schema_column_names = self.get_column_names('information_schema.COLUMNS')
        sql = """SELECT * from information_schema.COLUMNS 
                  WHERE TABLE_SCHEMA ='%s' AND TABLE_NAME = '%s' and COLUMN_NAME='%s'""" \
              % (self.get_database_name(), table, column)
        self.cursor.execute(sql)
        return dict(zip(information_schema_column_names, self.cursor.fetchone()))

    def get_columns_information_schema(self, table):
        """
        function which returns the entry in the information_schema.COLUMNS as list of dictionary for all columns of one table
        format of return value [{'Column_from_information_schema':value,...},..]"""
        information_schema_column_names = self.get_column_names(self, 'information_schema.COLUMNS')
        sql = "SELECT * from information_schema.COLUMNS where TABLE_SCHEMA ='%s' AND TABLE_NAME = '%s'" \
              % (self.get_database_name(table))
        self.cursor.execute(sql)
        return [dict(zip(information_schema_column_names, x)) for x in self.cursor.fetchall()]

    def copy_table_structure(self, table2copy, newTableName):
        """
        copies a table to newTableName
        :param tabel2copy: table name to copy (string)
        :param newTableName: new table name (string)
        """
        self.cursor.execute("show create table `%s`" % table2copy)
        sql = re.sub('^CREATE *TABLE *`?(' + table2copy + ')`?', ("CREATE TABLE `%s`" % newTableName), self.cursor.fetchone()[1])
        return self.cursor.execute(sql)

    def optimize_data_types(self, tables=[], execute=True, **params):
        """
        optimize the data type and size of all columns in all given tables
        :param cursor: pymysql cursor
        :param tables: list of strings or string (table names or only one table name)
        :param params: parameter set {'enums':['list','of','enum','column','names'],...}  
        @return: optimizedColumnTypes [(column, optimized_type),...]
        optimize if table is not null
        NOT optimize: column is auto incremental
        Keep NULL attribute: column is designed to be NULL, not optimize to NOT NULL       
        """
        optimizedColumnTypes = []
        if type(tables) == str:
            tables = [tables]
        if len(tables) == 0:
            tables = self.get_table_names()
        for table in tables:
            print("try to optimize datatypes in table " + table)
            if not self.cursor.execute("SELECT * from `%s` limit 1" % table):  # if no entries available continue
                continue
            original_columns_dict = {}
            self.cursor.execute("describe %s" % table)
            for column in self.cursor.fetchall():
                column_name = column[0]
                column_type = column[1]
                original_columns_dict[column_name] = column_type
            if 'enums' in params:
                analysis = self.analyse_table(table, enums=params['enums'])
            else:
                analysis = self.analyse_table(table)
            for column in analysis.keys():
                if self.get_column_information_schema(table, column)['EXTRA'] == '':
                    optimized_type = analysis[column]['Optimal_fieldtype']
                    sql = "ALTER TABLE `%s` CHANGE `%s` `%s` %s;" % (table, column, column, optimized_type)
                    optimizedColumnTypes += [(column, optimized_type)]
                    if execute == True:
                        try:
                            self.cursor.execute(sql)
                        except:
                            print("error when execute %s" % (sql))
                            sys.exit()
        return optimizedColumnTypes

    def get_view_names(self):
        """get all view names"""
        database = self.get_database_name()
        self.cursor.execute("""SELECT TABLE_NAME 
            FROM  information_schema.TABLES 
            WHERE 
              TABLE_SCHEMA='%s' AND 
              TABLE_TYPE='VIEW'""" % database)
        return [x[0] for x in self.cursor.fetchall()]

    def view_exists(self, view):
        return view in self.get_view_names()

    def get_table_names(self):
        """get all table names"""
        database = self.get_database_name()
        self.cursor.execute(
            "SELECT TABLE_NAME from  information_schema.TABLES where TABLE_SCHEMA='%s' and TABLE_TYPE='BASE TABLE'" % database)
        return [x[0] for x in self.cursor.fetchall()]

    def table_exists(self, table):
        """return true if the specified table exists in the database"""
        return table in self.get_table_names()

    def get_column_names(self, table):
        self.cursor.execute("SHOW COLUMNS FROM %s" % table)
        return [x[0] for x in self.cursor.fetchall()]

    def get_column_type(self, table, column):
        database = self.get_database_name()
        self.cursor.execute("""SELECT DATA_TYPE 
            FROM `information_schema`.`COLUMNS` 
            WHERE 
              TABLE_NAME='%s' AND 
              COLUMN_NAME='%s' AND 
              TABLE_SCHEMA='%s'"""
                            % (table, column, database))
        return self.cursor.fetchone()[0]

    def fit4sql(self, obj, not_null=False):
        """fit strings for SQL statments"""
        if type(obj) == str:
            obj = "'" + pymysql.escape_string(obj.strip()) + "'"
        elif type(obj) == datetime.datetime:
            obj = "'" + str(obj) + "'"
        elif type(obj) in [list, tuple]:
            if len(obj) == 1:
                obj = self.fit4sql(obj[0])
        elif obj in [None, '']:
            if not_null:
                obj = "''"
            else:
                obj = "NULL"
        return str(obj)

    def csv2db_from_file(self, path_to_csv_file, **parameters):
        """Transfer from source file data to database. Creates automatically a new table the file name 
        if no table_name parameter is given.
        
        :param path_to_csv_file: absolute path to CSV file
        :param **parameters: table_name = name of table (string)
                             delimiter = charater sparate columns (string) default == tab stop
                             columns = list of column names in table (list or tuble)
                             field_enclosed_by = charater enclose fields
                             first_line_columns = True or False; default == False
                             database = use this database (default connected database)  
        """
        if not parameters.has_key('database'):
            parameters['database'] = self.database
        if not parameters.has_key('table_name'):
            parameters['table_name'] = os.path.split(path_to_csv_file)
        if not parameters.has_key('first_line_columns'):
            parameters['first_line_columns'] = False
        if not parameters.has_key('delimiter'):
            parameters['delimiter'] = "\t"
        first_line = True
        for line in open(path_to_csv_file):
            line = line.strip()
            if first_line:
                if parameters.has_key('columns'):
                    cols = parameters['columns']
                elif parameters['first_line_columns']:
                    cols = line.split(parameters['delimiter'])
                else:
                    cols = ["column_" + str(x) for x in range(len(line.split(parameters['delimiter'])))]
                len_cols = len(cols)
                colsSql = ", ".join(["`" + x + "` text NOT NULL" for x in cols])
                self.cursor.execute("CREATE TABLE `%s` (%s) TYPE=MyISAM" % (parameters['table_name'], colsSql))
                first_line = False
                if parameters['first_line_columns']:
                    continue
            value_list = [self.fit(x) for x in line.split(parameters['delimiter'])]
            insert_columns = (", ".join(value_list)) + (",''" * (len_cols - len(value_list)))
            self.cursor.execute("Insert into `%s` values(%s)" % (parameters['table_name'], insert_columns))

    def truncate_table(self, table, resetPrimaryKey=True):
        """truncate table"""
        self.cursor.execute("truncate " + table)
        if resetPrimaryKey:
            self.cursor.execute("ALTER TABLE %s AUTO_INCREMENT = 1" % table)

    def truncate_tables(self, tables):
        """truncate tables"""
        for table in tables:
            self.truncate_table(self, table)

    def truncate_all_tables(self, prefix=""):
        "truncates all tables from a database"
        self.cursor.execute("show tables")
        tables = [x[0] for x in self.cursor.fetchall()]
        if prefix:
            tables = [x for x in tables if x.starts_with(prefix)]
        for table in tables:
            self.cursor.execute("truncate `" + table + "`")
