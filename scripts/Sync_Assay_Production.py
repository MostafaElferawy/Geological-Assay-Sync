# -*- coding: utf-8 -*-
"""Build and validate a synchronized staging shapefile from an Excel assay table.

The production shapefile is read-only. This script creates a backup and a
separate staging shapefile; it NEVER promotes staging to production.

Target environment: ArcMap 10.8 / ArcPy / Python 2.7.
"""

import os
import sys
import math
import datetime
from collections import Counter

import arcpy

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import config

arcpy.env.overwriteOutput = False


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------

def log(message):
    print(message)


def normalize_id(value):
    """Retain the original workflow's ID normalization behavior.

    Numeric-looking values such as 123.0 are normalized to "123". This is
    intentionally retained for compatibility with the original workflow.
    """
    if value is None:
        return ""

    value = unicode(value).strip()
    if not value:
        return ""

    try:
        number = float(value)
        if number.is_integer():
            return str(int(number))
    except (TypeError, ValueError, OverflowError):
        pass

    return value


def is_numeric_id(value):
    try:
        int(value)
        return True
    except (TypeError, ValueError, OverflowError):
        return False


def is_finite_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return not (math.isnan(number) or math.isinf(number))


def is_valid_coordinate(value):
    if value is None or not is_finite_number(value):
        return False

    number = float(value)
    if config.ZERO_COORDINATE_IS_INVALID and number == 0:
        return False
    return True


def clean_value(value):
    if value is None:
        return None
    if isinstance(value, basestring):
        value = value.strip()
        if value == "":
            return None
    return value


def field_default(field):
    if field.type == "String":
        return ""
    if field.type in ("Integer", "SmallInteger"):
        return 0
    if field.type in ("Double", "Single"):
        return 0.0
    return None


def prepare_value(value, field):
    value = clean_value(value)

    if value is None:
        if field.isNullable:
            return None
        value = field_default(field)
        if value is None:
            raise Exception(
                "No safe default is available for non-nullable field: " +
                field.name
            )

    if field.type in ("Double", "Single"):
        if not is_finite_number(value):
            raise Exception("Invalid numeric value for field " + field.name)
        return float(value)

    if field.type in ("Integer", "SmallInteger"):
        if not is_finite_number(value):
            raise Exception("Invalid integer value for field " + field.name)
        numeric_value = float(value)
        if not numeric_value.is_integer():
            raise Exception("Fractional value supplied to integer field: " + field.name)
        return int(numeric_value)

    if field.type == "String":
        text_value = unicode(value)
        if field.length and len(text_value) > field.length:
            raise Exception(
                "Value exceeds field length for " + field.name +
                " (" + str(len(text_value)) + " > " + str(field.length) + ")"
            )
        return text_value

    return value


def make_geometry(east, north, spatial_reference):
    if not is_valid_coordinate(east) or not is_valid_coordinate(north):
        return None
    point = arcpy.Point(float(east), float(north))
    return arcpy.PointGeometry(point, spatial_reference)


def insert_record(cursor, record, geometry, output_fields):
    values = []
    for field in output_fields:
        values.append(prepare_value(record.get(field.name), field))
    cursor.insertRow([geometry] + values)


def unique_preserving_order(items):
    result = []
    seen = set()
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def ensure_folder(folder_path):
    if folder_path and not os.path.exists(folder_path):
        os.makedirs(folder_path)


def get_count(dataset):
    return int(arcpy.GetCount_management(dataset).getOutput(0))


def validate_configuration():
    required = [
        "EXCEL_PATH", "EXCEL_SHEET", "PRODUCTION_SHP", "STAGE_FOLDER",
        "GEODATABASE", "FIELD_MAP", "EXCEL_ID_FIELD", "SHAPE_ID_FIELD",
        "EXCEL_EASTING_FIELD", "EXCEL_NORTHING_FIELD",
        "SHAPE_EASTING_FIELD", "SHAPE_NORTHING_FIELD",
        "SPATIAL_REFERENCE_FACTORY_CODE", "PROTECTED_IDS",
        "NUMERIC_IDS_ONLY", "NEW_RECORD_DEFAULTS", "GEOMETRY_TOLERANCE"
    ]

    for name in required:
        if not hasattr(config, name):
            raise Exception("Missing configuration setting: " + name)

    if not isinstance(config.FIELD_MAP, dict) or not config.FIELD_MAP:
        raise Exception("FIELD_MAP must be a non-empty dictionary.")
    if not isinstance(config.PROTECTED_IDS, (set, list, tuple)):
        raise Exception("PROTECTED_IDS must be a set, list or tuple.")
    if not isinstance(config.NEW_RECORD_DEFAULTS, dict):
        raise Exception("NEW_RECORD_DEFAULTS must be a dictionary.")

    if config.EXCEL_ID_FIELD not in config.FIELD_MAP:
        raise Exception("EXCEL_ID_FIELD must be included in FIELD_MAP.")
    if config.FIELD_MAP[config.EXCEL_ID_FIELD] != config.SHAPE_ID_FIELD:
        raise Exception("ID field mapping does not match SHAPE_ID_FIELD.")
    if config.EXCEL_EASTING_FIELD not in config.FIELD_MAP:
        raise Exception("EXCEL_EASTING_FIELD must be included in FIELD_MAP.")
    if config.EXCEL_NORTHING_FIELD not in config.FIELD_MAP:
        raise Exception("EXCEL_NORTHING_FIELD must be included in FIELD_MAP.")
    if config.FIELD_MAP[config.EXCEL_EASTING_FIELD] != config.SHAPE_EASTING_FIELD:
        raise Exception("Easting field mapping does not match SHAPE_EASTING_FIELD.")
    if config.FIELD_MAP[config.EXCEL_NORTHING_FIELD] != config.SHAPE_NORTHING_FIELD:
        raise Exception("Northing field mapping does not match SHAPE_NORTHING_FIELD.")

    try:
        factory_code = int(config.SPATIAL_REFERENCE_FACTORY_CODE)
    except (TypeError, ValueError, OverflowError):
        raise Exception("SPATIAL_REFERENCE_FACTORY_CODE must be a valid factory code.")
    if factory_code <= 0:
        raise Exception("SPATIAL_REFERENCE_FACTORY_CODE must be greater than zero.")

    if float(config.GEOMETRY_TOLERANCE) < 0:
        raise Exception("GEOMETRY_TOLERANCE cannot be negative.")


def validate_spatial_reference(dataset_path, configured_factory_code):
    """Require Excel coordinates and production geometry to use the configured CRS."""
    source_sr = arcpy.Describe(dataset_path).spatialReference
    configured_sr = arcpy.SpatialReference(int(configured_factory_code))

    if source_sr is None or source_sr.name in (None, "", "Unknown"):
        raise Exception("Production shapefile has an unknown spatial reference.")
    if configured_sr is None or configured_sr.name in (None, "", "Unknown"):
        raise Exception("Configured spatial reference could not be created.")

    source_code = int(getattr(source_sr, "factoryCode", 0) or 0)
    configured_code = int(getattr(configured_sr, "factoryCode", 0) or 0)

    if source_code > 0 and configured_code > 0:
        if source_code != configured_code:
            raise Exception(
                "Spatial reference mismatch: production uses " +
                str(source_sr.name) + " (" + str(source_code) +
                "), while config.py specifies " + str(configured_sr.name) +
                " (" + str(configured_code) + "). Confirm the CRS of the Excel "
                "Easting/Northing values and set the configuration accordingly."
            )
    elif source_sr.exportToString() != configured_sr.exportToString():
        raise Exception(
            "Spatial reference definitions do not match. Confirm the CRS "
            "of both the production shapefile and Excel coordinates."
        )

    log("Spatial reference verified: " + str(source_sr.name))
    return source_sr


def validate_source_schema(production_path):
    description = arcpy.Describe(production_path)
    if str(description.shapeType).lower() != "point":
        raise Exception("Production input must be a POINT shapefile.")

    fields = arcpy.ListFields(production_path)
    field_names = [field.name for field in fields]
    required_shape_fields = unique_preserving_order(
        list(config.FIELD_MAP.values()) + [
            config.SHAPE_ID_FIELD,
            config.SHAPE_EASTING_FIELD,
            config.SHAPE_NORTHING_FIELD
        ]
    )

    for field_name in required_shape_fields:
        if field_name not in field_names:
            raise Exception("Required shapefile field not found: " + field_name)

    return fields


def read_excel_data(table):
    excel_fields = [field.name for field in arcpy.ListFields(table)]
    required_fields = unique_preserving_order(
        list(config.FIELD_MAP.keys()) + [
            config.EXCEL_ID_FIELD,
            config.EXCEL_EASTING_FIELD,
            config.EXCEL_NORTHING_FIELD
        ]
    )

    for field_name in required_fields:
        if field_name not in excel_fields:
            raise Exception("Missing Excel field after import: " + field_name)

    excel_data = {}
    eligible_ids = []
    blank_ids = 0
    invalid_ids = 0
    protected_excel = 0

    cursor = arcpy.da.SearchCursor(table, required_fields)
    try:
        for row in cursor:
            record = dict(zip(required_fields, row))
            sid = normalize_id(record.get(config.EXCEL_ID_FIELD))

            if not sid:
                blank_ids += 1
                continue
            if sid in config.PROTECTED_IDS:
                protected_excel += 1
                continue
            if config.NUMERIC_IDS_ONLY and not is_numeric_id(sid):
                invalid_ids += 1
                continue
            eligible_ids.append(sid)
    finally:
        del cursor

    counts = Counter(eligible_ids)
    duplicate_ids = set([sid for sid, count in counts.items() if count > 1])

    cursor = arcpy.da.SearchCursor(table, required_fields)
    try:
        for row in cursor:
            record = dict(zip(required_fields, row))
            sid = normalize_id(record.get(config.EXCEL_ID_FIELD))
            if not sid or sid in config.PROTECTED_IDS:
                continue
            if config.NUMERIC_IDS_ONLY and not is_numeric_id(sid):
                continue
            if sid in duplicate_ids:
                continue
            excel_data[sid] = record
    finally:
        del cursor

    stats = {
        "excel_count": get_count(table),
        "blank_ids": blank_ids,
        "invalid_ids": invalid_ids,
        "protected_excel": protected_excel,
        "duplicate_excel_ids": duplicate_ids
    }
    return excel_data, stats


def read_production_records(production_path, source_fields):
    attribute_names = [
        field.name for field in source_fields
        if field.type not in ("OID", "Geometry")
    ]

    for shape_field in config.FIELD_MAP.values():
        if shape_field not in attribute_names:
            raise Exception("Mapped shapefile field not found: " + shape_field)

    cursor_fields = attribute_names + ["SHAPE@"]
    records = []
    all_ids = []

    cursor = arcpy.da.SearchCursor(production_path, cursor_fields)
    try:
        for row in cursor:
            record = dict(zip(attribute_names, row[:-1]))
            record["SHAPE"] = row[-1]
            sid = normalize_id(record.get(config.SHAPE_ID_FIELD))
            records.append(record)
            if sid:
                all_ids.append(sid)
    finally:
        del cursor

    counts = Counter(all_ids)
    duplicate_ids = set([sid for sid, count in counts.items() if count > 1])
    return records, attribute_names, set(all_ids), duplicate_ids


def create_verified_backup(production_path, backup_path, source_count, source_sr):
    log("Creating production backup...")
    arcpy.CopyFeatures_management(production_path, backup_path)
    backup_count = get_count(backup_path)
    if backup_count != source_count:
        raise Exception("BACKUP VALIDATION FAILED: record count mismatch.")

    backup_sr = arcpy.Describe(backup_path).spatialReference
    if backup_sr is None or backup_sr.exportToString() != source_sr.exportToString():
        raise Exception("BACKUP VALIDATION FAILED: spatial reference mismatch.")

    log("Backup verified: " + backup_path)


def main():
    log("=" * 65)
    log("GEOLOGICAL ASSAY SYNCHRONIZATION - STAGING BUILD")
    log("=" * 65)

    validate_configuration()

    if not os.path.exists(config.EXCEL_PATH):
        raise Exception("Excel input file not found: " + config.EXCEL_PATH)
    if not arcpy.Exists(config.PRODUCTION_SHP):
        raise Exception("Production shapefile not found: " + config.PRODUCTION_SHP)

    source_fields = validate_source_schema(config.PRODUCTION_SHP)
    spatial_reference = validate_spatial_reference(
        config.PRODUCTION_SHP,
        config.SPATIAL_REFERENCE_FACTORY_CODE
    )

    # Prepare the geodatabase and import/validate Excel BEFORE making a backup.
    if not arcpy.Exists(config.GEODATABASE):
        if config.CREATE_GDB_IF_MISSING:
            gdb_parent = os.path.dirname(config.GEODATABASE)
            ensure_folder(gdb_parent)
            arcpy.CreateFileGDB_management(
                gdb_parent, os.path.basename(config.GEODATABASE)
            )
        else:
            raise Exception(
                "Geodatabase not found. Create it first or set "
                "CREATE_GDB_IF_MISSING = True in config.py."
            )

    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    table = os.path.join(config.GEODATABASE, config.INPUT_TABLE_NAME)
    output_shp = os.path.join(
        config.STAGE_FOLDER, config.STAGING_PREFIX + run_id + ".shp"
    )
    backup = os.path.join(config.GEODATABASE, config.BACKUP_PREFIX + run_id)

    if arcpy.Exists(output_shp):
        raise Exception("Staging output already exists: " + output_shp)
    if arcpy.Exists(backup):
        raise Exception("Backup already exists: " + backup)

    if arcpy.Exists(table):
        arcpy.Delete_management(table)

    log("Importing Excel...")
    arcpy.ExcelToTable_conversion(config.EXCEL_PATH, table, config.EXCEL_SHEET)
    excel_data, excel_stats = read_excel_data(table)

    log("Excel records: " + str(excel_stats["excel_count"]))
    log("Eligible unique Excel IDs: " + str(len(excel_data)))
    log("Duplicate Excel IDs: " + str(len(excel_stats["duplicate_excel_ids"])))
    log("Blank IDs: " + str(excel_stats["blank_ids"]))
    log("Invalid IDs: " + str(excel_stats["invalid_ids"]))
    log("Protected Excel rows: " + str(excel_stats["protected_excel"]))

    log("Reading production shapefile...")
    source_count = get_count(config.PRODUCTION_SHP)
    existing_records, source_attribute_names, existing_ids, duplicate_shape_ids = \
        read_production_records(config.PRODUCTION_SHP, source_fields)

    log("Existing production records: " + str(len(existing_records)))
    log("Duplicate Shapefile IDs: " + str(len(duplicate_shape_ids)))
    log("Existing attribute fields retained: " + str(len(source_attribute_names)))

    # Validate default-field names before any backup or staging write.
    source_attribute_set = set(source_attribute_names)
    for field_name in config.NEW_RECORD_DEFAULTS.keys():
        if field_name not in source_attribute_set:
            raise Exception("NEW_RECORD_DEFAULTS field not found: " + field_name)

    # Backup is created only after the input/schema prechecks have passed.
    create_verified_backup(
        config.PRODUCTION_SHP, backup, source_count, spatial_reference
    )

    ensure_folder(config.STAGE_FOLDER)
    out_folder = os.path.dirname(output_shp)
    out_name = os.path.basename(output_shp)

    log("Creating staging shapefile...")
    arcpy.CreateFeatureclass_management(
        out_folder,
        out_name,
        "POINT",
        config.PRODUCTION_SHP,
        "DISABLED",
        "DISABLED",
        spatial_reference
    )

    output_fields = [
        field for field in arcpy.ListFields(output_shp)
        if field.type not in ("OID", "Geometry")
    ]
    output_names = [field.name for field in output_fields]

    for field_name in source_attribute_names:
        if field_name not in output_names:
            raise Exception("Source attribute field missing from staging: " + field_name)

    for field_name in config.FIELD_MAP.values():
        if field_name not in output_names:
            raise Exception("Mapped output field missing: " + field_name)

    insert_fields = ["SHAPE@"] + output_names
    insert_cursor = arcpy.da.InsertCursor(output_shp, insert_fields)

    updated = 0
    added = 0
    preserved = 0
    deleted = 0
    null_geometry = 0
    valid_geometry = 0

    try:
        # Update or preserve every existing production record.
        for old_record in existing_records:
            sid = normalize_id(old_record.get(config.SHAPE_ID_FIELD))

            preserve_record = (
                sid in config.PROTECTED_IDS
                or sid in excel_stats["duplicate_excel_ids"]
                or sid in duplicate_shape_ids
                or not sid
                or (config.NUMERIC_IDS_ONLY and not is_numeric_id(sid))
            )

            if preserve_record:
                insert_record(
                    insert_cursor, old_record, old_record.get("SHAPE"), output_fields
                )
                preserved += 1
                if old_record.get("SHAPE") is None:
                    null_geometry += 1
                else:
                    valid_geometry += 1
                continue

            if sid not in excel_data:
                deleted += 1
                continue

            new_record = dict(old_record)
            excel_record = excel_data[sid]
            for excel_field, shape_field in config.FIELD_MAP.items():
                new_record[shape_field] = excel_record.get(excel_field)

            geometry = make_geometry(
                excel_record.get(config.EXCEL_EASTING_FIELD),
                excel_record.get(config.EXCEL_NORTHING_FIELD),
                spatial_reference
            )
            insert_record(insert_cursor, new_record, geometry, output_fields)
            updated += 1
            if geometry is None:
                null_geometry += 1
            else:
                valid_geometry += 1

        # Add eligible Excel IDs that do not exist anywhere in production.
        for sid in excel_data:
            if sid in existing_ids:
                continue

            excel_record = excel_data[sid]
            new_record = {}
            for field in output_fields:
                new_record[field.name] = None

            for field_name, default_value in config.NEW_RECORD_DEFAULTS.items():
                new_record[field_name] = default_value
            for excel_field, shape_field in config.FIELD_MAP.items():
                new_record[shape_field] = excel_record.get(excel_field)

            geometry = make_geometry(
                excel_record.get(config.EXCEL_EASTING_FIELD),
                excel_record.get(config.EXCEL_NORTHING_FIELD),
                spatial_reference
            )
            insert_record(insert_cursor, new_record, geometry, output_fields)
            added += 1
            if geometry is None:
                null_geometry += 1
            else:
                valid_geometry += 1
    finally:
        del insert_cursor

    # Output count validation.
    output_count = get_count(output_shp)
    expected_count = updated + added + preserved

    log("=" * 65)
    log("STAGING BUILD SUMMARY")
    log("=" * 65)
    log("Updated records: " + str(updated))
    log("Added records: " + str(added))
    log("Preserved records: " + str(preserved))
    log("Deleted records: " + str(deleted))
    log("Output total: " + str(output_count))
    log("Valid geometries: " + str(valid_geometry))
    log("Null geometries: " + str(null_geometry))

    if output_count != expected_count:
        raise Exception("OUTPUT COUNT VALIDATION FAILED.")
    if valid_geometry + null_geometry != output_count:
        raise Exception("GEOMETRY COUNT VALIDATION FAILED.")

    # Geometry-to-coordinate validation, preserving the original strict rule.
    log("Running geometry validation...")
    geometry_errors = []
    missing_geometry = []
    geometry_without_coords = []
    validation_cursor = arcpy.da.SearchCursor(
        output_shp,
        [config.SHAPE_ID_FIELD, config.SHAPE_EASTING_FIELD,
         config.SHAPE_NORTHING_FIELD, "SHAPE@"]
    )
    try:
        for sid, east, north, geometry in validation_cursor:
            coords_valid = (
                is_valid_coordinate(east) and is_valid_coordinate(north)
            )
            if geometry is None:
                if coords_valid:
                    missing_geometry.append(sid)
                continue
            if not coords_valid:
                geometry_without_coords.append(sid)
                continue

            point = geometry.firstPoint
            tolerance = float(config.GEOMETRY_TOLERANCE)
            if (abs(point.X - float(east)) > tolerance or
                    abs(point.Y - float(north)) > tolerance):
                geometry_errors.append(sid)
    finally:
        del validation_cursor

    log("Geometry mismatches: " + str(len(geometry_errors)))
    log("Valid coordinates without geometry: " + str(len(missing_geometry)))
    log("Geometry without valid coordinates: " + str(len(geometry_without_coords)))

    if geometry_errors:
        raise Exception("GEOMETRY COORDINATE MISMATCH.")
    if missing_geometry:
        raise Exception("VALID COORDINATES WITHOUT GEOMETRY.")
    if geometry_without_coords:
        raise Exception("GEOMETRY WITHOUT VALID COORDINATES.")

    # Final validation confirms that the production source was not changed.
    check_count = get_count(output_shp)
    final_source_count = get_count(config.PRODUCTION_SHP)
    if check_count != output_count:
        raise Exception("FINAL OUTPUT COUNT VALIDATION FAILED.")
    if final_source_count != source_count:
        raise Exception("ORIGINAL PRODUCTION RECORD COUNT CHANGED.")

    log("=" * 65)
    log("STAGING BUILD COMPLETED SUCCESSFULLY")
    log("=" * 65)
    log("RUN ID: " + run_id)
    log("OUTPUT: " + output_shp)
    log("BACKUP: " + backup)
    log("Original production records: " + str(final_source_count))
    log("New staging records: " + str(output_count))
    log("Original production shapefile was NOT modified.")
    log("All existing attribute fields were carried into staging.")
    log("Backup was verified.")
    log("This script does not promote staging to production.")
    log("=" * 65)


if __name__ == "__main__":
    main()
