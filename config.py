# -*- coding: utf-8 -*-
"""User configuration for Geological Assay Data Synchronization.

Edit this file for your own project. The synchronization engine is kept
separate so it can be reused without editing its core logic.
Compatible with ArcMap 10.8 / ArcPy / Python 2.7.
"""

import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Input files
EXCEL_PATH = os.path.join(PROJECT_DIR, "sample_data", "Assay_Temp.xlsx")
EXCEL_SHEET = "Rock Sample Assay"
PRODUCTION_SHP = os.path.join(PROJECT_DIR, "data", "Data_Assay.shp")

# Output locations
STAGE_FOLDER = os.path.join(PROJECT_DIR, "output", "Production_Stage")
GEODATABASE = os.path.join(PROJECT_DIR, "output", "Sync_Production.gdb")
INPUT_TABLE_NAME = "Assay_Production_Input"
CREATE_GDB_IF_MISSING = False

# Coordinate reference system used by BOTH Excel Easting/Northing values
# and the production shapefile. Change this to the correct EPSG/factory code.
# Example: 32636 = WGS 84 / UTM zone 36N.
SPATIAL_REFERENCE_FACTORY_CODE = 32636
EXCEL_EASTING_FIELD = "East_x"
EXCEL_NORTHING_FIELD = "North_y"
SHAPE_EASTING_FIELD = "x"
SHAPE_NORTHING_FIELD = "y"
ZERO_COORDINATE_IS_INVALID = True

# Record identification and protection rules
EXCEL_ID_FIELD = "Sample_ID"
SHAPE_ID_FIELD = "Sample_ID"

# Empty by default. Add IDs here only when your own workflow requires them
# to be excluded from Excel synchronization and preserved in the shapefile.
# Do not publish company-specific IDs in a public repository.
PROTECTED_IDS = set()

# Preserve the original workflow: only integer-like Sample_ID values qualify.
NUMERIC_IDS_ONLY = True

# Excel field name : Shapefile field name
FIELD_MAP = {
    "Sample_ID": "Sample_ID",
    "From_": "From_",
    "To": "To",
    "East_x": "x",
    "North_y": "y",
    "Trench_Channel_ID": "Trench_Cha",
    "Sample_Type": "Sample_Typ",
    "Description": "Descriptio",
    "Au_ppm": "Au_ppm",
    "Lithology": "Lithology",
    "Alteration": "Alteration"
}

# Values assigned to fields when a new record is inserted.
# Unmapped fields otherwise receive an empty/type-appropriate default.
NEW_RECORD_DEFAULTS = {
    "Num": 0
}

STAGING_PREFIX = "Data_Assay_Build_"
BACKUP_PREFIX = "Backup_"

# Coordinate comparison tolerance in the shapefile's map units.
GEOMETRY_TOLERANCE = 0.001
