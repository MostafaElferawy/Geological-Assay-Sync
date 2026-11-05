# Manual validation checklist

Run these checks only in a disposable project copy with synthetic or approved test data. Do not use the live production workbook or Shapefile for destructive tests.

- [ ] ArcMap 10.8 Python 2.7 can import `arcpy` and execute the script.
- [ ] The configured Excel workbook and worksheet are found.
- [ ] Missing required Excel or Shapefile fields cause a clear failure before output creation.
- [ ] A mismatched or unknown coordinate reference system stops the run.
- [ ] A verified backup is created and its record count / CRS match the source.
- [ ] Existing eligible IDs are updated from Excel.
- [ ] New eligible Excel IDs are added to staging.
- [ ] Duplicate Excel IDs are excluded and corresponding source records are preserved.
- [ ] Duplicate source IDs are preserved without update or deletion.
- [ ] Blank, protected, and non-numeric IDs follow the configured preservation rules.
- [ ] Excel rows with missing or invalid coordinates remain represented with null geometry.
- [ ] Geometry coordinates match the configured Easting/Northing attributes within tolerance.
- [ ] Blank Excel values behave as intended for nullable and non-nullable Shapefile fields.
- [ ] The source Shapefile's record count and contents remain unchanged.
- [ ] A failed run leaves the source Shapefile unchanged and reports a useful error.
- [ ] Repeated runs create distinct timestamped outputs without overwriting previous outputs.

Record the ArcMap / Python version, test dataset version, expected counts, actual counts, and log path for every test run.
