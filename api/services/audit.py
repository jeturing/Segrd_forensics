"""
Centralized audit logging service.
Writes structured audit events to a rotating audit log file and optionally persists them to the DB.
"""
from __future__ import annotations

import json
import logging
from logging.handlers import TimedRotatingFileHandler
from typing import Any, Dict, Optional
from datetime import datetime

from api.config import settings
from api.database import get_db_context
from api.models.tools import AuditLog

_LOGGER = logging.getLogger("audit")


def _init_audit_logger():
    """Ensure an audit logger with a TimedRotatingFileHandler is configured."""
    if _LOGGER.handlers:
        return

    audit_path = settings.LOGS_DIR / settings.AUDIT_LOG_FILE_NAME
    handler = TimedRotatingFileHandler(
        filename=str(audit_path),
        when=settings.AUDIT_LOG_ROTATION_WHEN,
        interval=1,
        backupCount=settings.AUDIT_LOG_BACKUP_COUNT,
        encoding="utf-8",
        utc=True
    )
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    _LOGGER.addHandler(handler)
    _LOGGER.setLevel(logging.INFO)


def record_audit_event(
    action: str,
    action_type: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    severity: str = "info",
    persist_to_db: Optional[bool] = None,
    db_session: Optional[Any] = None
):
    """Record a structured audit event.

    - Always writes the event to `logs/audit.log` using a TimedRotatingFileHandler.
    - If `persist_to_db` is True (or if it is None and `settings.AUDIT_LOG_TO_DB` is True)
      the event is also persisted to the DB using `api.models.tools.AuditLog`.
    - If `db_session` is provided, it will be used for DB persistence instead of opening a new session.
    """
    _init_audit_logger()

    payload = {
        "action": action,
        "action_type": action_type,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
        "user_id": user_id,
        "tenant_id": tenant_id,
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat()
    }

    message = json.dumps(payload, default=str)

    if severity == "debug":
        _LOGGER.debug(message)
    elif severity == "warning":
        _LOGGER.warning(message)
    elif severity == "error":
        _LOGGER.error(message)
    else:
        _LOGGER.info(message)

    # Determine persistence setting
    if persist_to_db is None:
        persist_to_db = settings.AUDIT_LOG_TO_DB

    if not persist_to_db:
        return

    try:
        if db_session:
            sess = db_session
            created_here = False
        else:
            sess = None
            created_here = True

        if created_here:
            with get_db_context() as db:
                audit = AuditLog(
                    id=AuditLog.generate_id(),
                    action=action,
                    action_type=action_type,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=details or {},
                    user_id=user_id,
                    tenant_id=tenant_id
                )
                db.add(audit)
                db.commit()
        else:
            audit = AuditLog(
                id=AuditLog.generate_id(),
                action=action,
                action_type=action_type,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                user_id=user_id,
                tenant_id=tenant_id
            )
            sess.add(audit)
            sess.commit()
    except Exception as e:
        # Persisting to DB failed - log the error in the audit log file
        _LOGGER.error(json.dumps({"error": f"Failed to persist audit to DB: {e}", "payload": payload}))
