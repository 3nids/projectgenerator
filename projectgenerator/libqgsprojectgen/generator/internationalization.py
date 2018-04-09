# -*- coding: utf-8 -*-
"""
/***************************************************************************
    begin                :    09/04/18
    git sha              :    :%H$
    copyright            :    (C) 2018 by Denis Rouzaud
    email                :    denis@opengis.ch
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


import yaml

class Internationalization:
    """Allow internationalization by providing rules."""

    def __init__(self, i18n_file):
        with open(i18n_file, 'r') as stream:
        try:
            print(yaml.load(stream))
        except yaml.YAMLError as exc:
            print(exc)

    def replace(self, text):
        return text
