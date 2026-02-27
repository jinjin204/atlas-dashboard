
# Walkthrough: Phase 2 Enhancements

## Summary
Implemented PART column support, updated side determination logic, and improved calendar UI with navigation and persistence.

## Changes

### 1. Logic (`production_logic.py`)
- **PART Support**: Now recognizes `PART` column. Grouping is done by `TIMESTAMP`, `PROJECT`, and `PART`.
- **Side Logic**: `determine_side` now explicitly treats "base" as "Back" (裏).

### 2. UI (`app.py` & `logic.js`)
- **Calendar Navigation**: Added `Prev`, `Next`, and `Today` buttons to the calendar header.
- **Persistence**: Calendar view date is now saved in `localStorage`. Reloading the page (Streamlit rerun) will restore the last viewed month instead of resetting to today.
- **Inspector**: Added `PART` column to the debug table.

### 3. Guidelines (`rules.md`)
- Added **Communication** section: "If technical discussion is needed, propose structurally instead of implementing silently."

## Verification
- **Calendar**: Check that `Prev`/`Next` buttons appear. Navigate to a different month, reload the page, and verify it stays on that month.
- **Logic**: Ensure `PART` column data is reflected in the event title (e.g., "Project A (Part 1)").
