I have implemented **District-Level GEOINT Score Creation**.

**Changes:**
1.  **Modified Calculation Task:** Updated `backend/app/tasks/geoint_tasks.py` to include a district processing loop.
2.  **Logic:**
    *   After calculating scores for all Provinces, the system now iterates through all Districts.
    *   Districts inherit key metrics (Search Index, Trend, Competition) from their parent Province to ensure consistency.
    *   **District Specifics:** The calculation uses the specific population of the district for demographic fit, and applies a slight random variation to the search index to simulate local differences.
3.  **Result:** When you run "Calculate GEOINT" for a keyword, it will now generate scores for both Provinces (81) and Districts (~970), populating the map for the drill-down view.

**To enable this data:**
Please go to the frontend, select a keyword, and click **"GEOINT Hesapla"** (Calculate GEOINT). This will trigger the updated background task and populate the district scores.