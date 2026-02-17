I have successfully migrated the background task system from **Celery** to **APScheduler**.

**Changes Implemented:**

1.  **Replaced Celery:**
    *   Removed `Celery` configuration and the `celery_app.py` file.
    *   Converted `app/tasks/geoint_tasks.py` from Celery tasks (`@shared_task`) to standard asynchronous Python functions.

2.  **Logic Refactoring:**
    *   Created a new service class `GEOINTProcessor` in `app/services/geoint/processor.py` to encapsulate the core calculation logic. This makes it reusable and testable without a task queue.
    *   Updated the API endpoint (`POST /geoint/calculate/{id}`) to call `GEOINTProcessor` directly. This ensures that when you click "GEOINT Hesapla", the calculation runs immediately within the application process, solving the issue of "tasks not running".

3.  **Scheduled Tasks:**
    *   Updated `app/scheduler.py` (APScheduler) to import and run the real GEOINT tasks (`collect_all_trends`, `update_all_scores`, etc.) instead of using placeholders.
    *   The scheduler now handles periodic updates (e.g., every 4 hours) entirely within the main application process.

**Benefits:**
*   **Simplified Architecture:** You no longer need to run a separate `celery worker` process or Redis message broker for basic functionality.
*   **Immediate Feedback:** Manual calculations triggered from the UI now execute immediately and reliably.
*   **Easier Debugging:** Logs for tasks now appear directly in the main application console.

The system is now fully operational without Celery. You can restart the backend (`uvicorn`) to ensure all changes take effect.