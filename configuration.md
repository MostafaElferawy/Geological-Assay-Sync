# Configuration guide

All project-specific settings are in the root `config.py` file. Paths default to files inside this repository so the synthetic example can be run without editing absolute paths.

## Inputs

- `EXCEL_PATH`: workbook path.
- `EXCEL_SHEET`: worksheet name to import.
- `PRODUCTION_SHP`: point Shapefile used as the source template and read-only input.

The Excel worksheet must contain the configured identifier, coordinate, and mapped attribute fields. The Shapefile must contain the corresponding mapped output fields plus the configured coordinate attributes.

## Outputs

- `STAGE_FOLDER`: destination for timestamped staging Shapefiles.
- `GEODATABASE`: File Geodatabase used for the imported Excel table and verified source backups.
- `INPUT_TABLE_NAME`: imported Excel table name.
- `CREATE_GDB_IF_MISSING`: when `True`, the script creates the configured File Geodatabase if it does not exist.

## Coordinate reference system

`SPATIAL_REFERENCE_FACTORY_CODE` must describe the coordinate system used by both the Excel Easting/Northing values and the source Shapefile. The script validates the source Shapefile against this configured CRS. It does not reproject coordinates.

`ZERO_COORDINATE_IS_INVALID` controls whether zero values are treated as missing coordinates. `GEOMETRY_TOLERANCE` is expressed in the Shapefile's map units.

## Record identifiers

- `EXCEL_ID_FIELD` and `SHAPE_ID_FIELD` identify the join key.
- `PROTECTED_IDS` is an empty set in the public example. Add only identifiers you are authorized to protect in your own private configuration; never publish company-specific IDs.
- `NUMERIC_IDS_ONLY` controls whether non-numeric IDs are excluded from the eligible synchronization set.

The engine does not contain special business rules for particular sample labels such as `ONS` or `Dump`. Implement and test such rules explicitly in a private configuration or a reviewed code change before operational use.

## Field mapping

`FIELD_MAP` maps Excel column names to Shapefile field names. Shapefile field names are limited in length; configure the exact physical field names shown by ArcCatalog.

`NEW_RECORD_DEFAULTS` supplies values for selected fields when new records are inserted. Other fields receive type-appropriate defaults when needed.

## Operational safeguards

1. Keep production workbooks and Shapefiles outside the public repository.
2. Test with copies in a separate working directory.
3. Inspect the backup and staging outputs and the run summary.
4. Confirm record counts, duplicate handling, null geometry, coordinate consistency, and blank-value behavior.
5. Do not promote staging automatically; promotion is not implemented in this repository.
