# Implementation Plan: Restoring Original Calendar UI & System Integration

## Goal Description
Restore the "Strategic Mind & Pipeline" (PM) UI (Calendar, Map, Gantt, Goal Setting) as the primary interface for `atlas-hub`, replacing the temporary FullCalendar solution. This integration will visualize the strict Production Logs (14-column format with `PART` and `TIMESTAMP`) within the original PM Calendar UI.

## User Review Required
> [!IMPORTANT]
> **State Persistence Strategy**:
> The original PM UI relies on `localStorage` and manual file Save/Load for state (Goals, Tasks). Atlas Hub's `app.py` mainly provides read-only "Production Events".
> The integration will use `st.components.v1.html` to render the UI.
> - **Production Data**: Injected from Python (Read-Only).
> - **Goal/Task Data**: Managed client-side (Browser `localStorage` + JSON Import/Export), preserving the "Free Operation" feel.

## Proposed Changes

### Atlas Hub (`atlas-hub/`)

#### [NEW] [static/](file:///c:/Users/yjing/.gemini/atlas-hub/static/)
Create a `static` directory to host the original UI assets.
*   **[NEW]** `index.html`: Copied from `PM_Strategic Mind & Pipeline/20260119_V5.1/index.html`.
    *   *Modification*: Remove hardcoded `PM.productionEvents = []` reference if any, or prepare a script block for injection.
*   **[NEW]** `style.css`: Copied from `PM_Strategic Mind & Pipeline/20260119_V5.1/style.css`.
*   **[NEW]** `logic.js`: Copied from `PM_Strategic Mind & Pipeline/20260119_V5.1/logic.js`.
    *   *Modification*: Ensure `PM.productionEvents` can be populated externally.

#### [MODIFY] [app.py](file:///c:/Users/yjing/.gemini/atlas-hub/app.py)
*   **Remove**: FullCalendar logic and HTML template.
*   **Add**: Logic to read `static/index.html`, `style.css`, `logic.js`.
*   **Add**: Data Injection Logic.
    *   Convert `production_events` to JSON.
    *   Inject into HTML: `<script>PM.productionEvents = {events_json};</script>` before `logic.js` execution.
*   **Add**: `st.components.v1.html` call with the combined HTML content.

### Bridge Logic (Data Transformation)
The `production_logic.py` already produces a compatible format:
```python
{
    "title": "Project Name (Part)",
    "start": "YYYY-MM-DD",
    "color": "#...",
    "extendedProps": { "confidence": "...", "details": "..." }
}
```
`logic.js` (v5.1) already has rendering logic for this format in `renderCalendar`. No major JS changes needed for data visualization.

## Verification Plan
1.  **UI Rendering**: Confirm the "Strategic Mind" interface loads within Streamlit.
2.  **Data Injection**: Confirm production events from `atlas` logs appear on the calendar.
3.  **Interactivity**:
    *   Confirm dragging nodes works.
    *   Confirm clicking production events shows details/confirmation.
    *   Confirm switching views (Map <-> Calendar) works.
