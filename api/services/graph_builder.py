"""
Graph Builder Service - Construye grafos de incidentes estilo Microsoft Sentinel
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
import logging
from api.config import settings

logger = logging.getLogger(__name__)

EVIDENCE_DIR = settings.EVIDENCE_DIR


class GraphNode(BaseModel):
    """Nodo del grafo de ataque"""
    id: str
    type: str  # user, ip, device, mailbox_rule, oauth_app, ioc, file, process, risk_event
    label: str
    severity: str = "none"  # critical, high, medium, low, none
    metadata: Dict[str, Any] = {}


class GraphEdge(BaseModel):
    """Arista del grafo de ataque"""
    id: str
    source: str
    target: str
    relation: str  # LOGON_FROM, FORWARDED_TO, MATCHED_IOC, EXECUTED_PROCESS, etc.
    metadata: Dict[str, Any] = {}


class CaseGraph(BaseModel):
    """Grafo completo del caso"""
    case_id: str
    risk_score: int = 0
    classification: Optional[str] = None  # REAL, FALSE_POSITIVE
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    generated_at: str = ""


class GraphBuilderService:
    """Servicio para construir grafos de incidentes a partir de evidencia forense"""
    
    def __init__(self):
        self.evidence_dir = EVIDENCE_DIR
        self._node_id_counter = 0
        self._edge_id_counter = 0
    
    def _next_node_id(self, prefix: str) -> str:
        self._node_id_counter += 1
        return f"{prefix}-{self._node_id_counter}"
    
    def _next_edge_id(self) -> str:
        self._edge_id_counter += 1
        return f"edge-{self._edge_id_counter}"
    
    def build_case_graph(self, case_id: str, tenant_id: str = None) -> CaseGraph:
        """
        Construye el grafo de ataque para un caso específico
        
        1. Carga evidencias de ~/forensics-evidence/<case_id>/*
        2. Consulta parsers de M365 Graph API, Sparrow, Hawk, Loki, YARA
        3. Enlaza entidades y calcula risk_score
        """
        logger.info(f"🔧 Construyendo grafo para caso: {case_id}")
        
        self._node_id_counter = 0
        self._edge_id_counter = 0
        
        nodes = []
        edges = []
        risk_factors = []
        
        case_evidence_path = self.evidence_dir / case_id
        
        # 0. Parse M365 Graph API results (REAL DATA from Graph API)
        m365_nodes, m365_edges, m365_risks = self._parse_m365_graph_evidence(case_evidence_path)
        nodes.extend(m365_nodes)
        edges.extend(m365_edges)
        risk_factors.extend(m365_risks)
        
        # 1. Parse Sparrow results (M365 sign-ins, OAuth apps, etc.)
        sparrow_nodes, sparrow_edges, sparrow_risks = self._parse_sparrow_evidence(case_evidence_path)
        nodes.extend(sparrow_nodes)
        edges.extend(sparrow_edges)
        risk_factors.extend(sparrow_risks)
        
        # 2. Parse Hawk results (Exchange forensics, mailbox rules)
        hawk_nodes, hawk_edges, hawk_risks = self._parse_hawk_evidence(case_evidence_path)
        nodes.extend(hawk_nodes)
        edges.extend(hawk_edges)
        risk_factors.extend(hawk_risks)
        
        # 3. Parse Loki results (IOCs, malware)
        loki_nodes, loki_edges, loki_risks = self._parse_loki_evidence(case_evidence_path)
        nodes.extend(loki_nodes)
        edges.extend(loki_edges)
        risk_factors.extend(loki_risks)
        
        # 4. Parse YARA results (pattern matches)
        yara_nodes, yara_edges, yara_risks = self._parse_yara_evidence(case_evidence_path)
        nodes.extend(yara_nodes)
        edges.extend(yara_edges)
        risk_factors.extend(yara_risks)
        
        # 5. Parse Custom Nodes (added manually by investigator)
        custom_nodes_data, custom_edges_data = self._parse_custom_nodes(case_evidence_path)
        nodes.extend(custom_nodes_data)
        edges.extend(custom_edges_data)
        
        # 6. Calculate overall risk score
        risk_score = self._calculate_risk_score(risk_factors, nodes)
        
        # 7. Connect orphan nodes to related entities
        edges = self._infer_connections(nodes, edges)
        
        # Remove duplicate nodes by ID
        seen_ids = set()
        unique_nodes = []
        for node in nodes:
            if node.id not in seen_ids:
                unique_nodes.append(node)
                seen_ids.add(node.id)
        
        return CaseGraph(
            case_id=case_id,
            risk_score=risk_score,
            nodes=unique_nodes,
            edges=edges,
            generated_at=datetime.utcnow().isoformat()
        )
    
    def _parse_m365_graph_evidence(self, case_path: Path) -> tuple:
        """Parsea resultados de M365 Graph API (DATOS REALES del tenant)"""
        nodes = []
        edges = []
        risks = []
        
        m365_path = case_path / "m365_graph"
        if not m365_path.exists():
            logger.debug(f"No hay evidencia M365 Graph en {m365_path}")
            return nodes, edges, risks
        
        logger.info(f"📊 Parseando evidencia M365 Graph desde {m365_path}")
        
        try:
            # 1. Parse Risky Sign-ins
            risky_signins_file = m365_path / "risky_signins.json"
            if risky_signins_file.exists():
                with open(risky_signins_file, 'r') as f:
                    risky_signins = json.load(f)
                    
                for signin in risky_signins:
                    # Create user node
                    upn = signin.get("userPrincipalName", "unknown")
                    user_id = f"user-{upn}"
                    
                    risk_level = signin.get("riskLevelDuringSignIn", "none")
                    severity_map = {"high": "critical", "medium": "high", "low": "medium"}
                    severity = severity_map.get(risk_level, "medium")
                    
                    if not any(n.id == user_id for n in nodes):
                        nodes.append(GraphNode(
                            id=user_id,
                            type="user",
                            label=signin.get("userDisplayName", upn),
                            severity=severity,
                            metadata={
                                "upn": upn,
                                "risk_level": risk_level,
                                "risk_state": signin.get("riskState"),
                                "app_used": signin.get("appDisplayName")
                            }
                        ))
                    
                    # Create IP node
                    ip_addr = signin.get("ipAddress")
                    if ip_addr:
                        ip_id = f"ip-{ip_addr}"
                        location = signin.get("location", {})
                        city = location.get("city", "Unknown")
                        country = location.get("countryOrRegion", "Unknown")
                        
                        # Check for suspicious countries
                        suspicious_countries = ["RU", "CN", "IR", "KP", "NG", "UA"]
                        is_suspicious = country in suspicious_countries
                        
                        if not any(n.id == ip_id for n in nodes):
                            nodes.append(GraphNode(
                                id=ip_id,
                                type="ip",
                                label=ip_addr,
                                severity="critical" if is_suspicious else "high",
                                metadata={
                                    "city": city,
                                    "country": country,
                                    "suspicious": is_suspicious
                                }
                            ))
                            if is_suspicious:
                                risks.append(("suspicious_country", 30))
                        
                        edges.append(GraphEdge(
                            id=self._next_edge_id(),
                            source=ip_id,
                            target=user_id,
                            relation="LOGON_FROM"
                        ))
                    
                    if risk_level == "high":
                        risks.append(("high_risk_signin", 25))
                    elif risk_level == "medium":
                        risks.append(("medium_risk_signin", 10))
            
            # 2. Parse Risky Users
            risky_users_file = m365_path / "risky_users.json"
            if risky_users_file.exists():
                with open(risky_users_file, 'r') as f:
                    risky_users = json.load(f)
                
                for user in risky_users:
                    upn = user.get("userPrincipalName", "unknown")
                    user_id = f"user-{upn}"
                    risk_level = user.get("riskLevel", "none")
                    
                    if not any(n.id == user_id for n in nodes):
                        nodes.append(GraphNode(
                            id=user_id,
                            type="user",
                            label=user.get("userDisplayName", upn),
                            severity="critical" if risk_level == "high" else "high",
                            metadata={
                                "upn": upn,
                                "risk_level": risk_level,
                                "risk_state": user.get("riskState"),
                                "risk_detail": user.get("riskDetail")
                            }
                        ))
                    
                    if risk_level == "high":
                        risks.append(("high_risk_user", 30))
            
            # 3. Parse OAuth Consents
            oauth_file = m365_path / "oauth_consents.json"
            if oauth_file.exists():
                with open(oauth_file, 'r') as f:
                    oauth_apps = json.load(f)
                
                dangerous_perms = ["Mail.Read", "Mail.Send", "Files.ReadWrite", "User.ReadWrite", "Directory.ReadWrite"]
                
                for app in oauth_apps:
                    scope = app.get("scope", "")
                    app_name = app.get("appDisplayName", app.get("clientId", "Unknown App"))
                    
                    # Check for dangerous permissions
                    is_dangerous = any(perm in scope for perm in dangerous_perms)
                    
                    if is_dangerous:
                        app_id = f"oauth-{app.get('clientId', app_name)}"
                        
                        if not any(n.id == app_id for n in nodes):
                            nodes.append(GraphNode(
                                id=app_id,
                                type="oauth_app",
                                label=app_name,
                                severity="high",
                                metadata={
                                    "scope": scope,
                                    "publisher": app.get("appPublisher", "Unknown"),
                                    "consent_type": app.get("consentType")
                                }
                            ))
                            risks.append(("risky_oauth_app", 20))
                        
                        # Connect to principal if exists
                        principal_id = app.get("principalId")
                        if principal_id:
                            edges.append(GraphEdge(
                                id=self._next_edge_id(),
                                source=f"user-{principal_id}",
                                target=app_id,
                                relation="CONSENTED"
                            ))
            
            # 4. Parse Inbox Rules
            inbox_rules_file = m365_path / "inbox_rules.json"
            if inbox_rules_file.exists():
                with open(inbox_rules_file, 'r') as f:
                    inbox_rules = json.load(f)
                
                for rule in inbox_rules:
                    if rule.get("isSuspicious"):
                        rule_id = self._next_node_id("rule")
                        rule_name = rule.get("displayName", "Unknown Rule")
                        upn = rule.get("userPrincipalName", "unknown")
                        
                        actions = rule.get("actions", {})
                        forward_to = actions.get("forwardTo", [])
                        redirect_to = actions.get("redirectTo", [])
                        
                        target = forward_to or redirect_to
                        target_str = str(target[0] if target else "Unknown")
                        
                        nodes.append(GraphNode(
                            id=rule_id,
                            type="mailbox_rule",
                            label=f"Rule: {rule_name[:30]}",
                            severity="critical",
                            metadata={
                                "rule_name": rule_name,
                                "forward_to": target_str,
                                "delete_enabled": actions.get("delete", False),
                                "move_to_deleted": actions.get("moveToFolder") == "deleteditems"
                            }
                        ))
                        risks.append(("suspicious_inbox_rule", 35))
                        
                        # Connect to user
                        user_id = f"user-{upn}"
                        if not any(n.id == user_id for n in nodes):
                            nodes.append(GraphNode(
                                id=user_id,
                                type="user",
                                label=upn,
                                severity="high",
                                metadata={"upn": upn}
                            ))
                        
                        edges.append(GraphEdge(
                            id=self._next_edge_id(),
                            source=user_id,
                            target=rule_id,
                            relation="CREATED"
                        ))
            
            # 5. Parse Users Analysis
            users_file = m365_path / "users_analysis.json"
            if users_file.exists():
                with open(users_file, 'r') as f:
                    users = json.load(f)
                
                for user in users:
                    upn = user.get("upn", "unknown")
                    user_id = f"user-{upn}"
                    
                    if not any(n.id == user_id for n in nodes):
                        nodes.append(GraphNode(
                            id=user_id,
                            type="user",
                            label=user.get("displayName", upn),
                            severity="low",
                            metadata={
                                "upn": upn,
                                "enabled": user.get("enabled"),
                                "last_signin": user.get("lastSignIn")
                            }
                        ))
            
            logger.info(f"✅ Parseados {len(nodes)} nodos y {len(edges)} aristas de M365 Graph")
            
        except Exception as e:
            logger.error(f"Error parsing M365 Graph evidence: {e}", exc_info=True)
        
        return nodes, edges, risks
    
    def _parse_sparrow_evidence(self, case_path: Path) -> tuple:
        """Parsea resultados de Sparrow (M365 forensics)"""
        nodes = []
        edges = []
        risks = []
        
        sparrow_path = case_path / "sparrow"
        if not sparrow_path.exists():
            return nodes, edges, risks
        
        try:
            # Parse suspicious sign-ins
            signin_files = list(sparrow_path.glob("*SignIns*.csv"))
            for signin_file in signin_files:
                with open(signin_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Create user node
                        user_id = f"user-{row.get('userPrincipalName', 'unknown')}"
                        if not any(n.id == user_id for n in nodes):
                            severity = "high" if row.get('riskLevel') in ['high', 'atRisk'] else "medium"
                            nodes.append(GraphNode(
                                id=user_id,
                                type="user",
                                label=row.get('userPrincipalName', 'Unknown'),
                                severity=severity,
                                metadata={
                                    "upn": row.get('userPrincipalName'),
                                    "risk_level": row.get('riskLevel'),
                                    "risk_state": row.get('riskState')
                                }
                            ))
                            if severity == "high":
                                risks.append(("user_high_risk", 25))
                        
                        # Create IP node
                        ip_addr = row.get('ipAddress')
                        if ip_addr:
                            ip_id = f"ip-{ip_addr}"
                            if not any(n.id == ip_id for n in nodes):
                                # Suspicious if from unexpected country
                                location = row.get('location', '')
                                is_suspicious = any(c in location.lower() for c in ['russia', 'china', 'iran', 'north korea'])
                                nodes.append(GraphNode(
                                    id=ip_id,
                                    type="ip",
                                    label=ip_addr,
                                    severity="critical" if is_suspicious else "low",
                                    metadata={
                                        "location": location,
                                        "client_app": row.get('clientAppUsed')
                                    }
                                ))
                                if is_suspicious:
                                    risks.append(("suspicious_ip", 30))
                            
                            # Create edge
                            edges.append(GraphEdge(
                                id=self._next_edge_id(),
                                source=ip_id,
                                target=user_id,
                                relation="LOGON_FROM"
                            ))
            
            # Parse OAuth applications
            oauth_files = list(sparrow_path.glob("*OAuth*.csv"))
            for oauth_file in oauth_files:
                with open(oauth_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        app_name = row.get('displayName', row.get('appDisplayName', 'Unknown'))
                        app_id = f"oauth-{row.get('appId', app_name)}"
                        
                        # Determine severity
                        permissions = row.get('scope', row.get('permissions', '')).lower()
                        high_risk_perms = ['mail.read', 'files.read', 'user.read.all', 'directory.read']
                        is_risky = any(p in permissions for p in high_risk_perms)
                        
                        nodes.append(GraphNode(
                            id=app_id,
                            type="oauth_app",
                            label=app_name,
                            severity="high" if is_risky else "medium",
                            metadata={
                                "app_id": row.get('appId'),
                                "permissions": permissions,
                                "publisher": row.get('publisherName', 'Unknown')
                            }
                        ))
                        
                        if is_risky:
                            risks.append(("risky_oauth_app", 20))
                        
                        # Connect to consenting user
                        consenter = row.get('principalDisplayName', row.get('userPrincipalName'))
                        if consenter:
                            user_id = f"user-{consenter}"
                            edges.append(GraphEdge(
                                id=self._next_edge_id(),
                                source=user_id,
                                target=app_id,
                                relation="CONSENTED"
                            ))
        
        except Exception as e:
            logger.error(f"Error parsing Sparrow evidence: {e}")
        
        return nodes, edges, risks
    
    def _parse_hawk_evidence(self, case_path: Path) -> tuple:
        """Parsea resultados de Hawk (Exchange forensics)"""
        nodes = []
        edges = []
        risks = []
        
        hawk_path = case_path / "hawk"
        if not hawk_path.exists():
            return nodes, edges, risks
        
        try:
            # Parse inbox rules
            rule_files = list(hawk_path.glob("*InboxRules*.csv")) + list(hawk_path.glob("*Rules*.csv"))
            for rule_file in rule_files:
                with open(rule_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        rule_name = row.get('Name', row.get('ruleName', 'Unknown Rule'))
                        forward_to = row.get('ForwardTo', row.get('forwardTo', ''))
                        redirect_to = row.get('RedirectTo', row.get('redirectTo', ''))
                        
                        # Check for suspicious forwarding
                        target = forward_to or redirect_to
                        if target and '@' in target:
                            # External forwarding detected
                            rule_id = self._next_node_id("rule")
                            severity = "critical" if not target.endswith(('.onmicrosoft.com', '.local')) else "medium"
                            
                            nodes.append(GraphNode(
                                id=rule_id,
                                type="mailbox_rule",
                                label=f"Forward: {rule_name}",
                                severity=severity,
                                metadata={
                                    "rule_name": rule_name,
                                    "forward_to": target,
                                    "enabled": row.get('Enabled', 'True')
                                }
                            ))
                            
                            if severity == "critical":
                                risks.append(("external_forwarding", 35))
                            
                            # Connect to mailbox owner
                            mailbox = row.get('MailboxOwnerId', row.get('Identity', ''))
                            if mailbox:
                                user_id = f"user-{mailbox}"
                                edges.append(GraphEdge(
                                    id=self._next_edge_id(),
                                    source=user_id,
                                    target=rule_id,
                                    relation="CREATED"
                                ))
            
            # Parse audit logs
            audit_files = list(hawk_path.glob("*Audit*.csv"))
            for audit_file in audit_files:
                with open(audit_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        operation = row.get('Operation', row.get('operation', ''))
                        
                        # High-risk operations
                        risky_ops = ['AddedToSecurityGroup', 'Set-Mailbox', 'New-InboxRule', 
                                    'Set-TransportRule', 'Add-MailboxPermission']
                        if operation in risky_ops:
                            risks.append(("risky_operation", 15))
        
        except Exception as e:
            logger.error(f"Error parsing Hawk evidence: {e}")
        
        return nodes, edges, risks
    
    def _parse_loki_evidence(self, case_path: Path) -> tuple:
        """Parsea resultados de Loki (IOC scanner)"""
        nodes = []
        edges = []
        risks = []
        
        loki_path = case_path / "loki"
        if not loki_path.exists():
            return nodes, edges, risks
        
        try:
            # Parse Loki output
            loki_files = list(loki_path.glob("*.csv")) + list(loki_path.glob("*.log"))
            for loki_file in loki_files:
                with open(loki_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Look for ALERT markers
                    if '[ALERT]' in content or 'ALERT' in content:
                        for line in content.split('\n'):
                            if '[ALERT]' in line or 'ALERT' in line:
                                ioc_id = self._next_node_id("ioc")
                                
                                # Extract file path
                                parts = line.split(';') if ';' in line else line.split()
                                file_path = parts[1] if len(parts) > 1 else line[:50]
                                
                                nodes.append(GraphNode(
                                    id=ioc_id,
                                    type="ioc",
                                    label=f"Alert: {file_path[:30]}",
                                    severity="critical",
                                    metadata={
                                        "alert": line[:200],
                                        "source": "Loki"
                                    }
                                ))
                                risks.append(("loki_alert", 40))
                    
                    if '[WARNING]' in content:
                        for line in content.split('\n'):
                            if '[WARNING]' in line:
                                ioc_id = self._next_node_id("ioc")
                                parts = line.split(';') if ';' in line else line.split()
                                file_path = parts[1] if len(parts) > 1 else line[:50]
                                
                                nodes.append(GraphNode(
                                    id=ioc_id,
                                    type="ioc",
                                    label=f"Warning: {file_path[:30]}",
                                    severity="high",
                                    metadata={
                                        "warning": line[:200],
                                        "source": "Loki"
                                    }
                                ))
                                risks.append(("loki_warning", 20))
        
        except Exception as e:
            logger.error(f"Error parsing Loki evidence: {e}")
        
        return nodes, edges, risks
    
    def _parse_yara_evidence(self, case_path: Path) -> tuple:
        """Parsea resultados de YARA"""
        nodes = []
        edges = []
        risks = []
        
        yara_path = case_path / "yara"
        if not yara_path.exists():
            return nodes, edges, risks
        
        try:
            yara_files = list(yara_path.glob("*.txt")) + list(yara_path.glob("*.log"))
            for yara_file in yara_files:
                with open(yara_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        # YARA output format: RuleName FilePath
                        parts = line.strip().split(' ', 1)
                        if len(parts) >= 2:
                            rule_name = parts[0]
                            file_path = parts[1]
                            
                            ioc_id = self._next_node_id("yara")
                            nodes.append(GraphNode(
                                id=ioc_id,
                                type="ioc",
                                label=f"YARA: {rule_name}",
                                severity="high",
                                metadata={
                                    "rule": rule_name,
                                    "file": file_path,
                                    "source": "YARA"
                                }
                            ))
                            risks.append(("yara_match", 30))
        
        except Exception as e:
            logger.error(f"Error parsing YARA evidence: {e}")
        
        return nodes, edges, risks
    
    def _parse_custom_nodes(self, case_path: Path) -> tuple:
        """Parsea nodos personalizados agregados manualmente por investigadores"""
        nodes = []
        edges = []
        
        custom_nodes_file = case_path / "custom_nodes.json"
        custom_edges_file = case_path / "custom_edges.json"
        
        try:
            # Parse custom nodes
            if custom_nodes_file.exists():
                logger.info(f"📝 Cargando nodos personalizados desde {custom_nodes_file}")
                with open(custom_nodes_file, 'r') as f:
                    custom_nodes_data = json.load(f)
                    
                for node_id, node_data in custom_nodes_data.items():
                    nodes.append(GraphNode(
                        id=node_id,
                        type=node_data.get("type", "custom_indicator"),
                        label=node_data.get("label", node_id),
                        severity=node_data.get("severity", "medium"),
                        metadata={
                            **node_data.get("metadata", {}),
                            "source": "manual",
                            "added_by": "investigator",
                            "notes": node_data.get("notes"),
                            "linked_users": node_data.get("linked_users"),
                            "linked_devices": node_data.get("linked_devices")
                        }
                    ))
                    logger.info(f"✅ Nodo personalizado agregado: {node_id}")
            
            # Parse custom edges
            if custom_edges_file.exists():
                logger.info(f"📝 Cargando aristas personalizadas desde {custom_edges_file}")
                with open(custom_edges_file, 'r') as f:
                    custom_edges_data = json.load(f)
                    
                for edge_data in custom_edges_data:
                    edges.append(GraphEdge(
                        id=edge_data.get("id", self._next_edge_id()),
                        source=edge_data.get("source"),
                        target=edge_data.get("target"),
                        relation=edge_data.get("relation", "RELATED_TO"),
                        metadata={
                            "source_field": edge_data.get("source_field", "manual"),
                            "strength": edge_data.get("strength", "medium"),
                            "evidence": edge_data.get("evidence"),
                            "added_by": "investigator"
                        }
                    ))
                    logger.info(f"✅ Arista personalizada agregada: {edge_data.get('relation')}")
        
        except Exception as e:
            logger.error(f"Error parsing custom nodes/edges: {e}")
        
        return nodes, edges
    
    def _calculate_risk_score(self, risk_factors: List[tuple], nodes: List[GraphNode]) -> int:
        """Calcula el risk score general del caso (0-100)"""
        base_score = sum(factor[1] for factor in risk_factors)
        
        # Add points for critical/high severity nodes
        critical_count = sum(1 for n in nodes if n.severity == "critical")
        high_count = sum(1 for n in nodes if n.severity == "high")
        
        base_score += critical_count * 10
        base_score += high_count * 5
        
        # Cap at 100
        return min(100, base_score)
    
    def _infer_connections(self, nodes: List[GraphNode], edges: List[GraphEdge]) -> List[GraphEdge]:
        """Infiere conexiones adicionales entre nodos relacionados"""
        # Get all connected node IDs
        connected = set()
        for edge in edges:
            connected.add(edge.source)
            connected.add(edge.target)
        
        # Connect orphan IOCs to users if they share the same case
        user_nodes = [n for n in nodes if n.type == "user"]
        ioc_nodes = [n for n in nodes if n.type == "ioc" and n.id not in connected]
        
        # If we have orphan IOCs and users, connect them
        if user_nodes and ioc_nodes:
            primary_user = user_nodes[0]  # Use first user as primary
            for ioc in ioc_nodes:
                edges.append(GraphEdge(
                    id=self._next_edge_id(),
                    source=primary_user.id,
                    target=ioc.id,
                    relation="RELATED_TO"
                ))
        
        return edges


# Singleton instance
graph_builder = GraphBuilderService()
