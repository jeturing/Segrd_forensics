"""
Evidence and Command Log Integration for Reports
=================================================
Extends report generation to include external evidence and command traceability
"""

import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from api.models.evidence_management import ExternalEvidence, EvidenceAssociation
from api.services.command_logger import command_logger

logger = logging.getLogger(__name__)


class ReportEvidenceCollector:
    """Collects evidence and command logs for report generation"""

    @staticmethod
    def collect_case_evidence(case_id: str, db: Session) -> Dict[str, Any]:
        """
        Collect all evidence associated with a case for report inclusion.

        Returns:
            Dictionary with evidence summary and details
        """
        # Get all evidence associations for this case
        associations = (
            db.query(EvidenceAssociation)
            .filter(
                EvidenceAssociation.entity_type == "case",
                EvidenceAssociation.entity_id == case_id,
            )
            .all()
        )

        evidence_items = []
        total_size = 0
        evidence_by_type = {}
        evidence_by_tool = {}

        for assoc in associations:
            evidence = (
                db.query(ExternalEvidence)
                .filter(ExternalEvidence.id == assoc.evidence_id)
                .first()
            )

            if evidence:
                evidence_items.append(
                    {
                        "id": evidence.id,
                        "name": evidence.name,
                        "type": evidence.evidence_type,
                        "file_name": evidence.file_name,
                        "file_size": evidence.file_size,
                        "sha256": evidence.file_hash_sha256,
                        "collected_by": evidence.collected_by,
                        "collected_from": evidence.collected_from,
                        "uploaded_at": (
                            evidence.uploaded_at.isoformat()
                            if evidence.uploaded_at
                            else None
                        ),
                        "verified": evidence.integrity_verified,
                        "association_relevance": assoc.relevance,
                        "tags": evidence.tags or [],
                    }
                )

                total_size += evidence.file_size or 0

                # Count by type
                etype = evidence.evidence_type
                evidence_by_type[etype] = evidence_by_type.get(etype, 0) + 1

                # Count by tool
                if evidence.source_tool_id:
                    from api.models.evidence_management import EvidenceSource

                    source = (
                        db.query(EvidenceSource)
                        .filter(EvidenceSource.id == evidence.source_tool_id)
                        .first()
                    )
                    if source:
                        tool_name = source.tool_name
                        evidence_by_tool[tool_name] = (
                            evidence_by_tool.get(tool_name, 0) + 1
                        )

        return {
            "total_items": len(evidence_items),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "evidence_by_type": evidence_by_type,
            "evidence_by_tool": evidence_by_tool,
            "evidence_items": evidence_items,
        }

    @staticmethod
    def collect_case_commands(case_id: str, db: Session) -> Dict[str, Any]:
        """
        Collect all command executions for a case for report inclusion.

        Returns:
            Dictionary with command execution history and statistics
        """
        commands = command_logger.get_case_commands(
            db=db,
            case_id=case_id,
            limit=1000,  # Get all commands for comprehensive report
        )

        command_timeline = []
        commands_by_tool = {}
        commands_by_status = {"completed": 0, "failed": 0, "running": 0, "pending": 0}
        total_duration = 0

        for cmd in commands:
            command_timeline.append(
                {
                    "id": cmd.id,
                    "tool": cmd.tool_name,
                    "command": (
                        cmd.command[:100] + "..."
                        if len(cmd.command) > 100
                        else cmd.command
                    ),
                    "status": cmd.status,
                    "executed_by": cmd.executed_by,
                    "started_at": (
                        cmd.started_at.isoformat() if cmd.started_at else None
                    ),
                    "duration_seconds": cmd.duration_seconds,
                    "exit_code": cmd.exit_code,
                }
            )

            # Count by tool
            tool = cmd.tool_name
            commands_by_tool[tool] = commands_by_tool.get(tool, 0) + 1

            # Count by status
            status = cmd.status
            commands_by_status[status] = commands_by_status.get(status, 0) + 1

            # Sum duration
            if cmd.duration_seconds:
                total_duration += cmd.duration_seconds

        return {
            "total_commands": len(commands),
            "commands_by_tool": commands_by_tool,
            "commands_by_status": commands_by_status,
            "total_duration_seconds": total_duration,
            "total_duration_minutes": round(total_duration / 60, 1),
            "command_timeline": command_timeline,
        }

    @staticmethod
    def generate_evidence_section_html(case_id: str, db: Session) -> str:
        """
        Generate HTML section for evidence in reports.

        Returns:
            HTML string with evidence details
        """
        evidence_data = ReportEvidenceCollector.collect_case_evidence(case_id, db)

        html = f"""
        <h2>Evidence Summary</h2>
        <div class="evidence-summary">
            <p><strong>Total Evidence Items:</strong> {evidence_data['total_items']}</p>
            <p><strong>Total Size:</strong> {evidence_data['total_size_mb']} MB</p>
        </div>
        
        <h3>Evidence by Type</h3>
        <table class="evidence-table">
            <thead>
                <tr>
                    <th>Type</th>
                    <th>Count</th>
                </tr>
            </thead>
            <tbody>
        """

        for etype, count in evidence_data["evidence_by_type"].items():
            html += f"""
                <tr>
                    <td>{etype}</td>
                    <td>{count}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        
        <h3>Evidence Items</h3>
        <table class="evidence-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Size</th>
                    <th>SHA256</th>
                    <th>Collected By</th>
                    <th>Verified</th>
                </tr>
            </thead>
            <tbody>
        """

        for item in evidence_data["evidence_items"]:
            size_str = (
                f"{round(item['file_size'] / (1024*1024), 2)} MB"
                if item["file_size"]
                else "N/A"
            )
            sha256_short = item["sha256"][:16] + "..." if item["sha256"] else "N/A"
            verified_icon = "✓" if item["verified"] else "✗"

            html += f"""
                <tr>
                    <td>{item['id']}</td>
                    <td>{item['name']}</td>
                    <td>{item['type']}</td>
                    <td>{size_str}</td>
                    <td><code>{sha256_short}</code></td>
                    <td>{item['collected_by'] or 'Unknown'}</td>
                    <td>{verified_icon}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        </div>
        """

        return html

    @staticmethod
    def generate_commands_section_html(case_id: str, db: Session) -> str:
        """
        Generate HTML section for command execution history in reports.

        Returns:
            HTML string with command details
        """
        commands_data = ReportEvidenceCollector.collect_case_commands(case_id, db)

        html = f"""
        <h2>Command Execution History</h2>
        <div class="commands-summary">
            <p><strong>Total Commands Executed:</strong> {commands_data['total_commands']}</p>
            <p><strong>Total Execution Time:</strong> {commands_data['total_duration_minutes']} minutes</p>
            <p><strong>Status:</strong> 
                Completed: {commands_data['commands_by_status']['completed']}, 
                Failed: {commands_data['commands_by_status']['failed']}, 
                Running: {commands_data['commands_by_status']['running']}
            </p>
        </div>
        
        <h3>Commands by Tool</h3>
        <table class="commands-table">
            <thead>
                <tr>
                    <th>Tool</th>
                    <th>Executions</th>
                </tr>
            </thead>
            <tbody>
        """

        for tool, count in commands_data["commands_by_tool"].items():
            html += f"""
                <tr>
                    <td>{tool}</td>
                    <td>{count}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        
        <h3>Command Timeline</h3>
        <table class="commands-table">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Tool</th>
                    <th>Command</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Executed By</th>
                </tr>
            </thead>
            <tbody>
        """

        for cmd in commands_data["command_timeline"]:
            status_class = (
                "success"
                if cmd["status"] == "completed"
                else "error" if cmd["status"] == "failed" else "warning"
            )
            duration_str = (
                f"{cmd['duration_seconds']}s" if cmd["duration_seconds"] else "N/A"
            )

            html += f"""
                <tr>
                    <td>{cmd['started_at'] or 'N/A'}</td>
                    <td>{cmd['tool']}</td>
                    <td><code>{cmd['command']}</code></td>
                    <td><span class="{status_class}">{cmd['status']}</span></td>
                    <td>{duration_str}</td>
                    <td>{cmd['executed_by'] or 'system'}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        </div>
        """

        return html

    @staticmethod
    def generate_chain_of_custody_section(case_id: str, db: Session) -> Dict[str, Any]:
        """
        Generate chain of custody section for evidence reports.

        Returns:
            Dictionary with chain of custody details for all evidence
        """
        associations = (
            db.query(EvidenceAssociation)
            .filter(
                EvidenceAssociation.entity_type == "case",
                EvidenceAssociation.entity_id == case_id,
            )
            .all()
        )

        custody_records = []

        for assoc in associations:
            evidence = (
                db.query(ExternalEvidence)
                .filter(ExternalEvidence.id == assoc.evidence_id)
                .first()
            )

            if evidence and evidence.custody_chain:
                custody_records.append(
                    {
                        "evidence_id": evidence.id,
                        "evidence_name": evidence.name,
                        "chain": evidence.custody_chain,
                    }
                )

        return {
            "total_evidence": len(custody_records),
            "custody_records": custody_records,
        }


# Export collector instance
evidence_collector = ReportEvidenceCollector()
