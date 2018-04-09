# -*- coding: utf-8 -*-

"""
/***************************************************************************
                              -------------------
        begin                : 2018
        copyright            : (C) 2018 by OPENGIS.ch
        email                : info@opengis.ch
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

from ...qgissettingmanager import *

class Settings(SettingManager):
    def __init__(self):
        SettingManager.__init__(self, "projectgenerator")
        self.add_setting( String("i18n_file", Scope.Project, os.path.abspath(os.path.abspath(__file__)+"../i18n/en.yml"))
