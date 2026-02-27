# Logic Update: Strict Timestamp Enforcement

## Summary of Changes
I have updated `production_logic.py` to **strictly usage the timestamp column** for determining production dates.

### 1. `logic/production_logic.py`: Disable Filename Fallback
- **Removed Fallback**: The logic that extracted dates from filenames (e.g., `20200101_Part.nc`) has been commented out/disabled.
- **Strict Timestamp**: The system now exclusively relies on the `timestamp` (or `日時`) column.
- **Handling Missing Data**: If a log entry behaves a valid timestamp, it is treated as "date unknown" and is **excluded** from the calendar.

### benefit
- **Accuracy**: This ensures that re-running old NC programs today will correctly show up as **Today's** production, not as production from years ago.

## Verification Steps
1.  **Run the App**: `streamlit run app.py`
2.  **Check Date**: Verify that recent machine runs appear on the correct current date.
3.  **Check Logs**: Confirm that no events are appearing in the distant past (unless the machine clock itself was wrong).

## Code Changes
- [production_logic.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/production_logic.py)
