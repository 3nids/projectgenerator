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
import re

from qgis.core import QgsProviderRegistry, QgsWkbTypes, QgsApplication
from qgis.PyQt.QtCore import QCoreApplication, QLocale

from projectgenerator.libqgsprojectgen.dataobjects import Field
from projectgenerator.libqgsprojectgen.dataobjects import LegendGroup
from projectgenerator.libqgsprojectgen.dataobjects.layers import Layer
from projectgenerator.libqgsprojectgen.dataobjects.relations import Relation
from ..dbconnector import pg_connector, gpkg_connector
from .config import IGNORED_SCHEMAS, IGNORED_TABLES, IGNORED_FIELDNAMES, READONLY_FIELDNAMES

class Generator:
    def __init__(self, tool_name, uri, inheritance, schema=None):
        self.tool_name = tool_name
        self.uri = uri
        self.inheritance = inheritance
        self.schema = schema or None
        if self.tool_name == 'ili2pg':
            self._db_connector = pg_connector.PGConnector(uri, schema)
        elif self.tool_name == 'ili2gpkg':
            self._db_connector = gpkg_connector.GPKGConnector(uri, None)

    def layers(self):
        tables_info = self._get_tables_info()
        layers = list()

        for record in tables_info:
            # When in PostGIS mode, leaving schema blank should load tables from
            # all schemas, except the ignored ones
            if self.schema:
                if record['schemaname'] != self.schema:
                    continue
            elif record['schemaname'] in IGNORED_SCHEMAS:
                continue

            if record['tablename'] in IGNORED_TABLES:
                continue

            if self.tool_name == 'ili2pg':
                provider = 'postgres'
                if record['geometry_column']:
                    data_source_uri = '{uri} key={primary_key} estimatedmetadata=true srid={srid} type={type} table="{schema}"."{table}" ({geometry_column})'.format(
                        uri=self.uri,
                        primary_key=record['primary_key'],
                        srid=record['srid'],
                        type=record['type'],
                        schema=record['schemaname'],
                        table=record['tablename'],
                        geometry_column=record['geometry_column']
                    )
                else:
                    data_source_uri = '{uri} key={primary_key} table="{schema}"."{table}"'.format(
                        uri=self.uri,
                        primary_key=record['primary_key'],
                        schema=record['schemaname'],
                        table=record['tablename']
                    )
            elif self.tool_name == 'ili2gpkg':
                provider = 'ogr'
                data_source_uri = '{uri}|layername={table}'.format(
                    uri=self.uri,
                    table=record['tablename']
                )

            alias = record['table_alias'] if 'table_alias' in record else ''
            is_domain = record['is_domain'] == 'ENUM' or record['is_domain'] == 'CATALOGUE' if 'is_domain' in record else False
            layer = Layer(provider,
                          data_source_uri,
                          record['tablename'],
                          record['geometry_column'],
                          QgsWkbTypes.parseType(record['type']) or QgsWkbTypes.Unknown,
                          alias,
                          is_domain)

            # Configure fields for current table
            fields_info = self._get_fields_info(record['tablename'])
            constraints_info = self._get_constraints_info(record['tablename'])
            re_iliname = re.compile('^@iliname (.*)$')

            for fielddef in fields_info:
                column_name = fielddef['column_name']
                comment = fielddef['comment']
                m = re_iliname.match(comment) if comment else None
                alias = fielddef['column_alias']
                if m and not alias:
                    alias = m.group(1)

                field = Field(column_name)
                field.alias = alias

                if column_name in IGNORED_FIELDNAMES:
                    field.widget = 'Hidden'

                if column_name in READONLY_FIELDNAMES:
                    field.read_only = True

                if column_name in constraints_info:
                    field.widget = 'Range'
                    field.widget_config['Min'] = constraints_info[column_name][0]
                    field.widget_config['Max'] = constraints_info[column_name][1]
                    field.widget_config['Suffix'] = fielddef['unit'] if 'unit' in fielddef else ''

                if 'texttype' in fielddef and fielddef['texttype'] == 'MTEXT':
                    field.widget = 'TextEdit'
                    field.widget_config['IsMultiline'] = True

                if 'time' in fielddef['data_type'] or 'date' in fielddef['data_type']:
                    field.widget = 'DateTime'
                    field.widget_config['calendar_popup'] = True

                    dateFormat = QLocale(QgsApplication.instance().locale()).dateFormat(QLocale.ShortFormat)
                    timeFormat = QLocale(QgsApplication.instance().locale()).timeFormat(QLocale.ShortFormat)
                    dateTimeFormat = QLocale(QgsApplication.instance().locale()).dateTimeFormat(QLocale.ShortFormat)

                    if 'time' in fielddef['data_type'] and not 'timestamp' in fielddef['data_type']:
                        field.widget_config['display_format'] = timeFormat
                    elif 'timestamp' in fielddef['data_type']:
                        field.widget_config['display_format'] = dateTimeFormat
                    elif 'date' in fielddef['data_type']:
                        field.widget_config['display_format'] = dateFormat

                layer.fields.append(field)

            layers.append(layer)

        return layers

    def relations(self, layers):
        relations_info = self._get_relations_info()
        mapped_layers = {layer.name: layer for layer in layers}
        relations = list()

        for record in relations_info:
            if record['referencing_table_name'] in mapped_layers.keys() and record['referenced_table_name'] in mapped_layers.keys():
                relation = Relation()
                relation.referencing_layer = mapped_layers[record['referencing_table_name']]
                relation.referenced_layer = mapped_layers[record['referenced_table_name']]
                relation.referencing_field = record['referencing_column_name']
                relation.referenced_field = record['referenced_column_name']
                relation.name = record['constraint_name']
                relations.append(relation)

        return relations

    def legend(self, layers):
        legend = LegendGroup(QCoreApplication.translate('LegendGroup', 'root'))
        tables = LegendGroup(QCoreApplication.translate('LegendGroup', 'tables'))
        domains = LegendGroup(QCoreApplication.translate('LegendGroup', 'domains'), False)

        point_layers = []
        line_layers = []
        polygon_layers = []

        for layer in layers:
            if layer.geometry_column:
                geometry_type = QgsWkbTypes.geometryType(layer.wkb_type)
                if geometry_type == QgsWkbTypes.PointGeometry:
                    point_layers.append(layer)
                elif geometry_type == QgsWkbTypes.LineGeometry:
                    line_layers.append(layer)
                elif geometry_type == QgsWkbTypes.PolygonGeometry:
                    polygon_layers.append(layer)
            else:
                if layer.is_domain:
                    domains.append(layer)
                else:
                    tables.append(layer)

        for l in point_layers:
            legend.append(l)
        for l in line_layers:
            legend.append(l)
        for l in polygon_layers:
            legend.append(l)

        if not tables.is_empty():
            legend.append(tables)
        if not domains.is_empty():
            legend.append(domains)

        return legend

    def _metadata_exists(self):
        return self._db_connector.metadata_exists()

    def _get_tables_info(self):
        return self._db_connector.get_tables_info()

    def _get_fields_info(self, table_name):
        return self._db_connector.get_fields_info(table_name)

    def _get_constraints_info(self, table_name):
        return self._db_connector.get_constraints_info(table_name)

    def _get_relations_info(self):
        return self._db_connector.get_relations_info()
