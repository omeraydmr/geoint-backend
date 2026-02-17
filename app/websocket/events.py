"""
WebSocket event types and emission functions.

Defines event structures and helper functions for sending real-time updates.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.websocket.manager import manager

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """WebSocket event types."""

    GEOINT_UPDATE = "geoint_update"
    COMPETITOR_CHANGE = "competitor_change"
    MEDIA_MENTION = "media_mention"
    TASK_NOTIFICATION = "task_notification"
    KEYWORD_ANALYSIS_COMPLETE = "keyword_analysis_complete"
    SYSTEM_NOTIFICATION = "system_notification"


class WebSocketEvent(BaseModel):
    """WebSocket event model."""

    event_type: EventType
    data: Dict[str, Any]
    timestamp: str
    user_id: Optional[str] = None


# ================================================================================
# Event Emission Functions
# ================================================================================

async def emit_geoint_update(
    user_id: str,
    keyword_id: str,
    score_data: Dict[str, Any]
):
    """
    Emit GEOINT score update event.

    Args:
        user_id: Target user ID
        keyword_id: Keyword that was updated
        score_data: Score calculation results
    """
    event = {
        "event_type": EventType.GEOINT_UPDATE.value,
        "data": {
            "keyword_id": keyword_id,
            "top_regions": score_data.get("top_regions", []),
            "avg_score": score_data.get("avg_score"),
            "total_regions": score_data.get("total_regions"),
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        await manager.send_personal_message(event, user_id)
        logger.info(f"GEOINT update sent to user {user_id} for keyword {keyword_id}")
    except Exception as e:
        logger.error(f"Failed to send GEOINT update: {e}")


async def emit_competitor_change(
    user_id: str,
    competitor_id: str,
    changes: Dict[str, Any]
):
    """
    Emit competitor metrics change event.

    Args:
        user_id: Target user ID
        competitor_id: Competitor that changed
        changes: Changed metrics
    """
    event = {
        "event_type": EventType.COMPETITOR_CHANGE.value,
        "data": {
            "competitor_id": competitor_id,
            "changes": changes,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        await manager.send_personal_message(event, user_id)
        logger.info(f"Competitor change sent to user {user_id} for competitor {competitor_id}")
    except Exception as e:
        logger.error(f"Failed to send competitor change: {e}")


async def emit_media_mention(
    user_id: str,
    mention_data: Dict[str, Any]
):
    """
    Emit new media mention event.

    Args:
        user_id: Target user ID
        mention_data: Media mention details
    """
    event = {
        "event_type": EventType.MEDIA_MENTION.value,
        "data": mention_data,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        await manager.send_personal_message(event, user_id)
        logger.info(f"Media mention sent to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send media mention: {e}")


async def emit_task_notification(
    user_id: str,
    task_id: str,
    status: str,
    message: Optional[str] = None
):
    """
    Emit task status notification.

    Args:
        user_id: Target user ID
        task_id: Task identifier
        status: Task status (completed, failed, etc.)
        message: Optional message
    """
    event = {
        "event_type": EventType.TASK_NOTIFICATION.value,
        "data": {
            "task_id": task_id,
            "status": status,
            "message": message,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        await manager.send_personal_message(event, user_id)
        logger.info(f"Task notification sent to user {user_id} for task {task_id}")
    except Exception as e:
        logger.error(f"Failed to send task notification: {e}")


async def emit_keyword_analysis_complete(
    user_id: str,
    keyword_id: str,
    results: Dict[str, Any]
):
    """
    Emit keyword analysis completion event.

    Args:
        user_id: Target user ID
        keyword_id: Keyword that was analyzed
        results: Analysis results
    """
    event = {
        "event_type": EventType.KEYWORD_ANALYSIS_COMPLETE.value,
        "data": {
            "keyword_id": keyword_id,
            "results": results,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        await manager.send_personal_message(event, user_id)
        logger.info(f"Keyword analysis complete sent to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send keyword analysis complete: {e}")


async def emit_system_notification(
    user_id: str,
    message: str,
    level: str = "info"
):
    """
    Emit system notification.

    Args:
        user_id: Target user ID
        message: Notification message
        level: Notification level (info, warning, error)
    """
    event = {
        "event_type": EventType.SYSTEM_NOTIFICATION.value,
        "data": {
            "message": message,
            "level": level,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        await manager.send_personal_message(event, user_id)
        logger.info(f"System notification sent to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send system notification: {e}")
