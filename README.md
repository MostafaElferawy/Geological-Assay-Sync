# Geological Assay Sync

A Python 2.7 / ArcPy utility for building and validating a **staging Shapefile** from an Excel assay table while preserving the source Shapefile.

> **Safety boundary:** this repository contains a staging-build engine only. It does not promote the staging output to the production Shapefile. Do not point it at operational company data until you have configured paths, reviewed the field mapping, and tested it on disposable copies.

## Features

- Imports an Excel worksheet into a File Geodatabase table.
- Validates required fields, record identifiers, and coordinate reference system.
- Creates and verifies a backup of the source point Shapefile.
- Builds a separate timestamped staging Shapefile.
- Updates eligible existing records, adds new eligible records, and reports records omitted from staging.
- Preserves records with blank, protected, non-numeric, or duplicate identifiers according to the configured rules.
- Retains existing attributes not included in the field mapping.
- Supports records without valid coordinates by writing null geometry.
- Checks geometry against coordinate attributes and confirms that the source record count did not change.

## Target environment

- Windows
- Esri ArcMap 10.8
- ArcPy supplied with ArcMap
- Python 2.7 (32-bit, ArcMap installation)

`arcpy` is not installed through `pip`. Run the script using the Python interpreter configured with ArcMap 10.8.

## Repository layout

```text
Geological-Assay-Sync/
├── config.py
├── scripts/
│   └── Sync_Assay_Production.py
├── sample_data/
│   └── Assay_Temp.xlsx
├── data/
│   ├── Data_Assay.shp
│   ├── Data_Assay.shx
│   ├── Data_Assay.dbf
│   ├── Data_Assay.prj
│   └── Data_Assay.cpg
├── output/
│   └── .gitkeep
├── docs/
│   └── configuration.md
└── tests/
    └── manual_validation_checklist.md
```

The workbook and Shapefile in this repository are small synthetic examples. They are not operational assay data.

## Quick start

1. Clone or download this repository to a local working directory.
2. Open `config.py` and verify every input path, field name, field mapping, ID rule, and CRS setting.
3. Keep the sample inputs for a demonstration, or replace them with **disposable copies** of your own input files.
4. Create `output/Sync_Production.gdb` in ArcCatalog, or set `CREATE_GDB_IF_MISSING = True` in `config.py`.
5. Ensure `output/Production_Stage/` exists; the script creates it if needed.
6. Run from the repository root:

```bat
C:\Python27\ArcGIS10.8\python.exe scripts\Sync_Assay_Production.py
```

Adjust the interpreter path to match your ArcMap installation.

## Configuration

See [docs/configuration.md](docs/configuration.md) before changing the project for another dataset.

## Output and safety behavior

- The source Shapefile is treated as read-only by this script.
- A timestamped backup is created in the configured File Geodatabase.
- A timestamped staging Shapefile is created in `output/Production_Stage/`.
- The script does **not** replace, rename, or promote the source Shapefile.
- Records absent from eligible Excel IDs are omitted from the staging output; review the summary before using that output for any downstream operation.
- Duplicate Excel IDs are excluded from the update set; corresponding source records are preserved.
- Duplicate source IDs are preserved and are not updated or deleted.
- Blank/protected/non-numeric source IDs are preserved according to `config.py`.
- Empty Excel values are passed through the configured field conversion logic; verify nullability and clearing behavior against your own Shapefile schema before operational use.

## Validation status

The source code has been prepared for a Python 2.7 / ArcMap 10.8 target. This environment does not include ArcPy, so a full runtime execution in ArcMap has **not** been performed as part of preparing this public package. Use the manual checklist in `tests/` in a disposable environment.

## Confidentiality

Never commit company workbooks, production Shapefiles, assay results, coordinates, customer or project identifiers, backups, lock files, geodatabases, machine-specific metadata, or internal file paths. Keep operational files outside this repository.

## Project status

Initial public packaging of the staging-build component. Production promotion, Excel/VBA event integration, and company-specific exception rules are intentionally outside this repository version.
