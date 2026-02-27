
# Walkthrough: Strict Column Logic Migration

## Summary
Rebuilt `production_logic.py` and `app.py` to strictly use CSV column names (`TIMESTAMP`, `PROJECT`, `PATH`) and removed all filename-based date parsing.

## Changes

### 1. Logic (`production_logic.py`)
- **Strict Column Use**: Now relies 100% on `TIMESTAMP` for dates, `PROJECT` for grouping, and `PATH` for side determination.
- **Removed**: All regex-based filename date extraction.
- **Safety**: Invalid timestamps are silently skipped (no errors).

### 2. UI (`app.py`)
- **Calendar**: Default view is now "Today" (2026-02).
- **Inspector**: Validation table now explicitly shows `TIMESTAMP`, `PROJECT`, `PATH` columns for debugging.
- **Cleanup**: Removed unused imports and legacy code.

## Verification
- **Check**: Ensure your CSV log file has the header row: `TIMESTAMP, ..., PROJECT, ..., PATH, ...`
- **Run**: `stream run app.py`
