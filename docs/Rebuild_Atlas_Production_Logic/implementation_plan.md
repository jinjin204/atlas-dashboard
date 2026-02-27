# Implementation Plan: PART Integration & Date Logic Correction

## 1. [Input] atlas/コード.js
**Target**: `c:\Users\yjing\.gemini\atlas\コード.js`

### Goals
1.  **PART Integration**: Insert `data.part` at Index 3.
2.  **Date Correction**: Stop using `data.date` (derived from filename) for `LOG_DATE` (Index 9). Use `data.timestamp` (execution time) instead.

### Code Change Proposal
```javascript
// ... inside appendRow ...
sheet.appendRow([
    data.timestamp,       // 0: TIMESTAMP (Execution Time)
    data.machine,         // 1: MACHINE
    data.project,         // 2: PROJECT
    data.part || "",      // 3: PART (New! Default to empty)
    data.process,         // 4: PROCESS (Shifted from 3)
    data.tool,            // 5: TOOL
    data.duration,        // 6: DURATION
    data.path,            // 7: PATH
    "",                   // 8: EXTRA_INFO
    data.timestamp,       // 9: LOG_DATE (FIX: Use TIMESTAMP, not data.date)
    data.side,            // 10: SIDE
    data.status,          // 11: STATUS
    data.remarks,         // 12: REMARKS
    JSON.stringify(data)  // 13: RAW_JSON
]);
```

## 2. [Display] atlas-hub/app.py
**Target**: `c:\Users\yjing\.gemini\atlas-hub\app.py`

### Goals
1.  **Syntax Fix**: Fix Python `f-string` errors by escaping JavaScript curly braces (`{` -> `{{`, `}` -> `}}`).
2.  **FullCalendar Config**: Ensure `headerToolbar` and `persistence` are correctly configured within the f-string.

### Code Change Proposal
- Wrap all JS function bodies in double braces: `eventClick: function(info) {{ ... }}`.
- Ensure `events: {events_json}` remains single braces for Python variable injection.

## 3. [Logic] logic/production_logic.py
**Target**: `c:\Users\yjing\.gemini\atlas-hub\logic\production_logic.py`

### Goals
1.  **Strict 14-Column Support**: Align with the new CSV structure.
2.  **Date Logic**: Confirm `TIMESTAMP` (Index 0) is used for all date calculations.
3.  **Part Grouping**: Group events by `PROJECT` + `PART`.

## Execution Order
1.  **User**: Accept this plan.
2.  **AI**: Apply changes to `atlas/コード.js` (User must deploy).
3.  **AI**: Apply changes to `atlas-hub/app.py`.
4.  **AI**: Apply changes to `logic/production_logic.py`.
