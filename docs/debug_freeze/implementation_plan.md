# System Reconstruction Plan

## Objective
Reconstruct `app.py`, `production_logic.py`, and `drive_utils.py` to fix date logic (strict timestamp), UI feedback (progress bar, clean status), and data accuracy (name matching, 90-day filter).

## Changes

### 1. `logic/drive_utils.py`
- **Imports**: Add `import streamlit as st` (only for progress text/bar).
- **Progress**: Use `st.empty` or similar to show progress during download.
- **Cleanup**: Ensure `st.empty().empty()` is called after completion to clear messages.

### 2. `logic/production_logic.py`
- **Date Source**: **Timestamp Column (1st column if missing)** only. **Disable** filename date logic.
- **Filtering**: Apply 90-day filter based on the *parsed timestamp column*.
- **Matching**: Group by product name and date. Check for 'Front' and 'Back'.
    - If both exist -> 'Pair (Front & Back)' (High Confidence)
    - If one exists -> 'Front Only' or 'Back Only' (Low Confidence)

### 3. `app.py`
- **Imports**: `from logic.drive_utils import load_data_from_drive`.
- **UI**:
    - `st.empty()` for loading status.
    - Calendar initialized to `new Date()` (Today) or `latest_event_date` if available.
    - **Debug List**: Display found events as a markdown list below the calendar.
- **Indentation**: Standard 4-space indentation.

## Verification
- Run `streamlit run app.py`.
- **Result**:
    - Calendar opens to Current Month (Feb 2026).
    - Events from today (from old files) appear on Today.
    - Loading message disappears.
    - Debug list shows matched events.
