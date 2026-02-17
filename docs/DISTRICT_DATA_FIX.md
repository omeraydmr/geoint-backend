## District Data Fix (v2 - Self-Healing)

### Problem

Legacy seed scripts created districts with fake placeholder names such as
"Adana 1", "Kuzey 3", "Guney 2". These names persisted because the
startup seed (`backend/app/core/seed.py`) only ran when the database was
completely empty. Once any data existed, it would skip re-seeding -- even
if the existing data contained fake names.

### Root Cause

The original `seed_geographic_data()` function had a single guard:

```python
if province_count > 0:
    return  # skip entirely
```

This meant databases seeded by older scripts could never self-correct.

### Fix Applied

1. **Self-healing detection:** On every startup, the seed function now
   samples existing district names and checks them against the pattern
   `/<word> <digits>$/` (e.g. "Adana 1", "Kuzey 3"). If any matches are
   found, it triggers a full district reseed.

2. **Authoritative data source:** All district names and polygon
   boundaries come from **geoBoundaries** (OpenStreetMap / GADM),
   providing 973 real Turkish district names with proper geometries.

3. **No manual intervention required:** The fix runs automatically on
   the next server startup. There is no need to manually clear the
   database or run a separate script.

### Data Sources

| Level     | Source                                      | Count |
|-----------|---------------------------------------------|-------|
| Provinces | geoBoundaries TUR ADM1 (simplified)         | 81    |
| Districts | geoBoundaries TUR ADM2 (simplified)         | ~973  |

### After Reseeding

After the automatic reseed completes, click **"GEOINT Hesapla"**
(Calculate GEOINT) in the dashboard to regenerate scores for the new
districts.
