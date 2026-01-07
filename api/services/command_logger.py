"""
MCP Kali Forensics - Command Logging Service
Comprehensive logging of forensic tool command executions
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from functools import wraps
import asyncio

from sqlalchemy.orm import Session

from api.models.evidence_management import CommandLog
from api.database import get_db_context

logger = logging.getLogger(__name__)


class CommandLogger:
    """Service for logging command executions"""

    @staticmethod
    def log_command(
        db: Session,
        command: str,
        tool_name: str,
        tool_version: Optional[str] = None,
        case_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
        analysis_id: Optional[str] = None,
        executed_by: Optional[str] = None,
        execution_host: Optional[str] = None,
        working_directory: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        input_files: Optional[List[str]] = None,
        environment_vars: Optional[Dict[str, str]] = None,
    ) -> CommandLog:
        """
        Create a new command log entry.

        Args:
            db: Database session
            command: Full command string
            tool_name: Name of the tool
            tool_version: Version of the tool
            case_id: Associated case ID
            evidence_id: Associated evidence ID
            analysis_id: Associated forensic analysis ID
            executed_by: User who executed the command
            execution_host: Hostname where executed
            working_directory: Working directory
            parameters: Parsed parameters as dict
            input_files: List of input files
            environment_vars: Relevant environment variables

        Returns:
            CommandLog object
        """
        cmd_log = CommandLog(
            command=command,
            tool_name=tool_name,
            tool_version=tool_version,
            case_id=case_id,
            evidence_id=evidence_id,
            analysis_id=analysis_id,
            executed_by=executed_by,
            execution_host=execution_host or os.uname().nodename,
            working_directory=working_directory or os.getcwd(),
            parameters=parameters,
            input_files=input_files,
            environment_vars=environment_vars,
            status="pending",
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )

        db.add(cmd_log)
        db.commit()
        db.refresh(cmd_log)

        logger.info(f"📝 Command logged: {cmd_log.id} - {tool_name}")

        return cmd_log

    @staticmethod
    def update_command_status(
        db: Session,
        command_id: str,
        status: str,
        exit_code: Optional[int] = None,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        output_files: Optional[List[str]] = None,
        output_summary: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> CommandLog:
        """
        Update command log with execution results.

        Args:
            db: Database session
            command_id: Command log ID
            status: Execution status (running, completed, failed)
            exit_code: Exit code from command
            stdout: Standard output (will be truncated if too long)
            stderr: Standard error (will be truncated if too long)
            output_files: List of files generated
            output_summary: Summary of results
            duration_seconds: Execution duration

        Returns:
            Updated CommandLog object
        """
        cmd_log = db.query(CommandLog).filter(CommandLog.id == command_id).first()

        if not cmd_log:
            raise ValueError(f"Command log {command_id} not found")

        cmd_log.status = status
        cmd_log.exit_code = exit_code

        # Truncate stdout/stderr if too long (keep last 10,000 chars)
        if stdout:
            cmd_log.stdout = stdout[-10000:] if len(stdout) > 10000 else stdout
        if stderr:
            cmd_log.stderr = stderr[-10000:] if len(stderr) > 10000 else stderr

        if output_files:
            cmd_log.output_files = output_files

        if output_summary:
            cmd_log.output_summary = output_summary

        if duration_seconds is not None:
            cmd_log.duration_seconds = duration_seconds

        if status in ["completed", "failed"]:
            cmd_log.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(cmd_log)

        logger.info(f"📝 Command {command_id} updated: {status}")

        return cmd_log

    @staticmethod
    def get_command_log(db: Session, command_id: str) -> Optional[CommandLog]:
        """Get command log by ID"""
        return db.query(CommandLog).filter(CommandLog.id == command_id).first()

    @staticmethod
    def get_case_commands(
        db: Session,
        case_id: str,
        tool_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[CommandLog]:
        """Get all commands for a case"""
        query = db.query(CommandLog).filter(CommandLog.case_id == case_id)

        if tool_name:
            query = query.filter(CommandLog.tool_name == tool_name)

        if status:
            query = query.filter(CommandLog.status == status)

        return query.order_by(CommandLog.started_at.desc()).limit(limit).all()

    @staticmethod
    def get_evidence_commands(
        db: Session, evidence_id: str, limit: int = 50
    ) -> List[CommandLog]:
        """Get all commands executed on an evidence"""
        return (
            db.query(CommandLog)
            .filter(CommandLog.evidence_id == evidence_id)
            .order_by(CommandLog.started_at.desc())
            .limit(limit)
            .all()
        )


def log_command_execution(
    tool_name: str,
    tool_version: Optional[str] = None,
    case_id_param: Optional[str] = "case_id",
    evidence_id_param: Optional[str] = "evidence_id",
):
    """
    Decorator to automatically log command executions.

    Usage:
        @log_command_execution("volatility", "3.0")
        async def run_volatility_analysis(case_id: str, memory_file: str, **kwargs):
            # ... execute volatility ...
            return results

    The decorator will:
    1. Create a command log entry before execution
    2. Update the log with results after execution
    3. Handle errors and log them
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract case_id and evidence_id from kwargs
            case_id = kwargs.get(case_id_param)
            evidence_id = kwargs.get(evidence_id_param)

            # Build command representation
            command_parts = [tool_name]
            for key, value in kwargs.items():
                if key not in [case_id_param, evidence_id_param]:
                    command_parts.append(f"--{key}={value}")
            command_str = " ".join(command_parts)

            # Create command log
            with get_db_context() as db:
                cmd_log = CommandLogger.log_command(
                    db=db,
                    command=command_str,
                    tool_name=tool_name,
                    tool_version=tool_version,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    parameters=kwargs,
                    executed_by=kwargs.get("executed_by", "system"),
                )
                command_id = cmd_log.id

            # Execute function
            start_time = time.time()
            try:
                # Update status to running
                with get_db_context() as db:
                    CommandLogger.update_command_status(
                        db=db, command_id=command_id, status="running"
                    )

                # Execute the actual function
                result = await func(*args, **kwargs)

                # Calculate duration
                duration = int(time.time() - start_time)

                # Update with success
                with get_db_context() as db:
                    CommandLogger.update_command_status(
                        db=db,
                        command_id=command_id,
                        status="completed",
                        exit_code=0,
                        duration_seconds=duration,
                        output_summary=(
                            json.dumps(result)
                            if isinstance(result, dict)
                            else str(result)[:500]
                        ),
                    )

                return result

            except Exception as e:
                # Calculate duration
                duration = int(time.time() - start_time)

                # Update with failure
                with get_db_context() as db:
                    CommandLogger.update_command_status(
                        db=db,
                        command_id=command_id,
                        status="failed",
                        exit_code=1,
                        stderr=str(e),
                        duration_seconds=duration,
                    )

                # Re-raise the exception
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Similar logic for sync functions
            case_id = kwargs.get(case_id_param)
            evidence_id = kwargs.get(evidence_id_param)

            command_parts = [tool_name]
            for key, value in kwargs.items():
                if key not in [case_id_param, evidence_id_param]:
                    command_parts.append(f"--{key}={value}")
            command_str = " ".join(command_parts)

            with get_db_context() as db:
                cmd_log = CommandLogger.log_command(
                    db=db,
                    command=command_str,
                    tool_name=tool_name,
                    tool_version=tool_version,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    parameters=kwargs,
                    executed_by=kwargs.get("executed_by", "system"),
                )
                command_id = cmd_log.id

            start_time = time.time()
            try:
                with get_db_context() as db:
                    CommandLogger.update_command_status(
                        db=db, command_id=command_id, status="running"
                    )

                result = func(*args, **kwargs)
                duration = int(time.time() - start_time)

                with get_db_context() as db:
                    CommandLogger.update_command_status(
                        db=db,
                        command_id=command_id,
                        status="completed",
                        exit_code=0,
                        duration_seconds=duration,
                        output_summary=(
                            json.dumps(result)
                            if isinstance(result, dict)
                            else str(result)[:500]
                        ),
                    )

                return result

            except Exception as e:
                duration = int(time.time() - start_time)

                with get_db_context() as db:
                    CommandLogger.update_command_status(
                        db=db,
                        command_id=command_id,
                        status="failed",
                        exit_code=1,
                        stderr=str(e),
                        duration_seconds=duration,
                    )

                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Singleton instance
command_logger = CommandLogger()
