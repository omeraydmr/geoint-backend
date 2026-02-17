I have successfully upgraded the **Isı Haritası (Heat Map)** section to enable deep-dive analysis into District (İlçe) level scores.

**Key Features Implemented:**
1.  **Drill-Down Interaction:** Users can now click on any Province (İl) on the map to "zoom in" and inspect detailed District (İlçe) scores for that specific province.
2.  **Auto-Zoom:** The map automatically zooms and pans to fit the selected region (Province or Turkey) when the view changes.
3.  **Back Navigation:** A "Türkiye Haritasına Dön" button allows users to easily return to the country-level view.

**Technical Changes:**
*   **Backend:** Updated `GET /geoint/heatmap/{keyword_id}` endpoint to accept an optional `province_id` parameter, enabling filtered district data retrieval.
*   **Frontend Context:** Enhanced `GEOINTContext` to support fetching heatmap data with specific region filters and geometry.
*   **Map Page:** Completely refactored `frontend/src/app/geoint/map/page.tsx` to use the advanced `HeatMap` component (rendering polygons instead of simple markers) and manage the drill-down state.
*   **Map Component:** Upgraded `HeatMap.js` with auto-fit bounds logic to handle dynamic zooming based on the loaded geographic data.

The Heat Map section is now fully interactive and supports the requested multi-level analysis.