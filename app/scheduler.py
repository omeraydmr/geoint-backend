"""
APScheduler configuration for background tasks

Replaces Celery for scheduled tasks with a lightweight in-process scheduler.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
import logging
from typing import Optional
from app.tasks.geoint_tasks import collect_all_trends, update_all_scores, check_alerts

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the scheduler instance"""
    global scheduler
    if scheduler is None:
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': True,  # Combine multiple missed jobs into one
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 300  # 5 minutes grace period
        }
        scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Europe/Istanbul'
        )
    return scheduler


# ============================================
# Scheduled Task Functions
# ============================================

async def update_all_competitors():
    """
    Update competitor metrics for all tracked competitors

    Runs daily at 3 AM
    """
    logger.info("Starting competitor update...")
    try:
        from app.core.database import get_db_session
        from sqlalchemy import select
        from app.models.competitor import Competitor

        async with get_db_session() as db:
            result = await db.execute(select(Competitor))
            competitors = result.scalars().all()

            logger.info(f"Updating {len(competitors)} competitors")

            for competitor in competitors:
                try:
                    # TODO: Implement actual competitor analysis
                    logger.debug(f"Updating competitor: {competitor.domain}")
                except Exception as e:
                    logger.error(f"Error updating {competitor.domain}: {e}")

        logger.info("Competitor update completed")
    except Exception as e:
        logger.error(f"Error in update_all_competitors: {e}")


async def crawl_all_mentions():
    """
    Crawl media mentions for all tracked brands

    Runs every 6 hours
    """
    logger.info("Starting media mention crawl...")
    try:
        # TODO: Implement media crawling
        logger.info("Media mention crawl completed")
    except Exception as e:
        logger.error(f"Error in crawl_all_mentions: {e}")


async def check_ai_visibility():
    """
    Check brand visibility in AI models (ChatGPT, Claude, Perplexity)

    Runs weekly (Sundays at 2 AM)
    """
    logger.info("Starting AI visibility check...")
    try:
        # TODO: Implement AI visibility checks
        logger.info("AI visibility check completed")
    except Exception as e:
        logger.error(f"Error in check_ai_visibility: {e}")


# ============================================
# Scheduler Setup
# ============================================

def setup_scheduled_jobs():
    """Configure all scheduled jobs"""
    sched = get_scheduler()

    # Collect Google Trends data every 4 hours
    sched.add_job(
        collect_all_trends,
        IntervalTrigger(hours=4),
        id='collect_trends',
        name='Collect Google Trends Data',
        replace_existing=True
    )

    # Update GEOINT scores every 6 hours
    sched.add_job(
        update_all_scores,
        IntervalTrigger(hours=6),
        id='update_scores',
        name='Update GEOINT Scores',
        replace_existing=True
    )

    # Check for alerts every hour
    sched.add_job(
        check_alerts,
        IntervalTrigger(hours=1),
        id='check_alerts',
        name='Check Trend Alerts',
        replace_existing=True
    )

    # Update competitor data daily at 3 AM
    sched.add_job(
        update_all_competitors,
        CronTrigger(hour=3, minute=0),
        id='update_competitors',
        name='Update Competitor Data',
        replace_existing=True
    )

    # Crawl media mentions every 6 hours
    sched.add_job(
        crawl_all_mentions,
        IntervalTrigger(hours=6),
        id='crawl_mentions',
        name='Crawl Media Mentions',
        replace_existing=True
    )

    # Check AI visibility weekly (Sundays at 2 AM)
    sched.add_job(
        check_ai_visibility,
        CronTrigger(day_of_week='sun', hour=2, minute=0),
        id='check_ai_visibility',
        name='Check AI Visibility',
        replace_existing=True
    )

    logger.info("Scheduled jobs configured")


async def start_scheduler():
    """Start the scheduler"""
    sched = get_scheduler()
    setup_scheduled_jobs()
    sched.start()
    logger.info("APScheduler started")

    # Log all scheduled jobs
    for job in sched.get_jobs():
        logger.info(f"  - {job.id}: {job.name} (next run: {job.next_run_time})")


async def stop_scheduler():
    """Stop the scheduler gracefully"""
    global scheduler
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("APScheduler stopped")
        scheduler = None


def get_job_status():
    """Get status of all scheduled jobs"""
    sched = get_scheduler()
    jobs = []
    for job in sched.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run_time': str(job.next_run_time) if job.next_run_time else None,
            'pending': job.pending,
        })
    return jobs
