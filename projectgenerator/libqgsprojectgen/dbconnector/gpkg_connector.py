# -*- coding: utf-8 -*-
"""
/***************************************************************************
    begin                :    04/10/17
    git sha              :    :%H$
    copyright            :    (C) 2017 by Germán Carrillo
    email                :    gcarrillo@linuxmail.org
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import sqlite3
import qgis.utils
from .db_connector import DBConnector

GPKG_METADATA_TABLE = 'T_ILI2DB_TABLE_PROP'

class GPKGConnector(DBConnector):
    def __init__(self, uri, schema):
        DBConnector.__init__(self, uri, schema)
        self.conn = qgis.utils.spatialite_connect(uri)
        self.conn.row_factory = sqlite3.Row
        self._bMetadataTable = self._metadata_exists()

    def map_data_types(self, data_type):
        '''GPKG date/time types correspond to QGIS date/time types'''
        return data_type.lower()

    def metadata_exists(self):
        return self._bMetadataTable

    def _metadata_exists(self):
        cursor = self.conn.cursor()
        cursor.execute("""SELECT count(name)
            FROM sqlite_master
            WHERE name = '{}';
                    """.format(GPKG_METADATA_TABLE))
        return cursor.fetchone()[0] == 1

    def get_tables_info(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT NULL AS schemaname, s.name AS tablename, NULL AS primary_key, g.column_name AS geometry_column, g.srs_id AS srid, g.geometry_type_name AS type, p.setting AS is_domain, alias.setting AS table_alias
            FROM sqlite_master s
            LEFT JOIN gpkg_geometry_columns g
               ON g.table_name = s.name
            LEFT JOIN T_ILI2DB_TABLE_PROP p
               ON p.tablename = s.name
                  AND p.tag = 'ch.ehi.ili2db.tableKind'
            LEFT JOIN t_ili2db_table_prop alias
               ON alias.tablename = s.name
                  AND alias.tag = 'ch.ehi.ili2db.dispName'
            WHERE s.type='table';
                       """)
        records = cursor.fetchall()

        # Get pk info and update each record storing it in a list of dicts
        complete_records = list()
        for record in records:
            cursor.execute("""
                PRAGMA table_info({})
                """.format(record['tablename']))
            table_info = cursor.fetchall()

            primary_key_list = list()
            for table_record in table_info:
                if table_record['pk'] > 0:
                    primary_key_list.append(table_record['name'])
            primary_key = ",".join(primary_key_list) or None

            dict_record = dict(zip(record.keys(), tuple(record)))
            dict_record['pk'] = primary_key
            complete_records.append(dict_record)

        cursor.close()
        return complete_records

    def get_fields_info(self, table_name):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info({});".format(table_name))
        columns_info = cursor.fetchall()

        cursor.execute("""
            SELECT *
            FROM t_ili2db_column_prop
            WHERE tablename = '{}'
            """.format(table_name))
        columns_prop = cursor.fetchall()

        complete_records = list()
        for column_info in columns_info:
            record = {}
            record['column_name'] = column_info['name']
            record['data_type'] = column_info['type']
            record['comment'] = None
            record['unit'] = None
            record['texttype'] = None
            record['column_alias'] = None

            for column_prop in columns_prop:
                if column_prop['columnname'] == column_info['name']:
                    if column_prop['tag'] == 'ch.ehi.ili2db.unit':
                        record['unit'] = column_prop['setting']
                    elif column_prop['tag'] == 'ch.ehi.ili2db.textKind':
                        record['texttype'] = column_prop['setting']
                    elif column_prop['tag'] == 'ch.ehi.ili2db.dispName':
                        record['column_alias'] = column_prop['setting']

            complete_records.append(record)

        cursor.close()
        return complete_records
