"""
HexStrike Red Team (v4.6) persistence models.
"""
from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, JSON, Text, ForeignKey

from api.database import Base


class RedTeamEngagement(Base):
    """Engagement definition and scoping metadata."""

    __tablename__ = "redteam_engagements"

    id = Column(String(50), primary_key=True)  # RT-XXXXXXXX
    name = Column(String(200), nullable=False)
    tenant_id = Column(String(64), index=True)
    scope = Column(JSON, default=[])
    rules_of_engagement = Column(JSON, default=[])
    owner = Column(String(100))
    tags = Column(JSON, default=[])
    status = Column(String(32), default="active", index=True)
    plan = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def generate_id() -> str:
        return f"RT-{uuid.uuid4().hex[:8].upper()}"


class RedTeamRun(Base):
    """Run issued to HexStrike for a specific target/tool."""

    __tablename__ = "redteam_runs"

    id = Column(String(60), primary_key=True)  # RTRUN-XXXX
    engagement_id = Column(String(50), ForeignKey("redteam_engagements.id"), nullable=False, index=True)
    target = Column(String(500), nullable=False)
    tool = Column(String(100), nullable=False)
    params = Column(JSON, default={})
    status = Column(String(32), default="running", index=True)
    hexstrike_pid = Column(String(64))
    result = Column(JSON, default={})
    error = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def generate_id() -> str:
        return f"RTRUN-{uuid.uuid4().hex[:8].upper()}"


class RedTeamFinding(Base):
    """Findings produced by HexStrike runs."""

    __tablename__ = "redteam_findings"

    id = Column(String(60), primary_key=True)  # RTF-XXXX
    engagement_id = Column(String(50), ForeignKey("redteam_engagements.id"), nullable=False, index=True)
    run_id = Column(String(60), ForeignKey("redteam_runs.id"), nullable=True, index=True)
    title = Column(String(300), nullable=False)
    severity = Column(String(16), default="medium", index=True)
    description = Column(Text)
    category = Column(String(64))
    evidence = Column(JSON, default={})
    tags = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def generate_id() -> str:
        return f"RTF-{uuid.uuid4().hex[:8].upper()}"
