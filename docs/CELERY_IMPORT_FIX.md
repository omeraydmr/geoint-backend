I have resolved the `ModuleNotFoundError: No module named 'app.tasks.celery_app'` error.

**Fix Applied:**
*   Updated `backend/app/tasks/__init__.py` to remove the import of the deleted `celery_app` module.

The application should now start successfully without Celery dependencies.