# Architecture Diagrams - MCP Kali Forensics

**Version:** v4.5.0  
**Date:** December 2024  
**Model:** C4 Architecture Model

---

## 📋 Overview

This document contains comprehensive architecture diagrams for the MCP Kali Forensics & IR Worker system, following the C4 model (Context, Container, Component, Code).

---

## 1. System Context Diagram (Level 1)

Shows how the MCP Forensics system fits into the broader environment.

```mermaid
graph TB
    subgraph External["External Systems"]
        M365[Microsoft 365<br/>Tenant]
        HIBP[Have I Been Pwned<br/>API]
        Dehashed[Dehashed<br/>API]
        VT[VirusTotal<br/>API]
        AbuseIPDB[AbuseIPDB<br/>API]
        Shodan[Shodan<br/>API]
    end
    
    subgraph Users["Users"]
        Admin[Security Admin]
        Analyst[SOC Analyst]
        Investigator[Forensic Investigator]
    end
    
    System[MCP Kali Forensics<br/>& IR Worker<br/>Automated forensic analysis<br/>and incident response]
    
    Admin -->|Manages system| System
    Analyst -->|Investigates incidents| System
    Investigator -->|Performs forensics| System
    
    System -->|Collects audit logs| M365
    System -->|Checks breaches| HIBP
    System -->|Queries leaks| Dehashed
    System -->|Scans files| VT
    System -->|Checks IPs| AbuseIPDB
    System -->|Searches assets| Shodan
    
    style System fill:#1e88e5,stroke:#1565c0,color:#fff
    style Admin fill:#4caf50,stroke:#388e3c,color:#fff
    style Analyst fill:#4caf50,stroke:#388e3c,color:#fff
    style Investigator fill:#4caf50,stroke:#388e3c,color:#fff
```

---

## 2. Container Diagram (Level 2)

Shows the high-level technical building blocks of the system.

```mermaid
graph TB
    subgraph Browser["Web Browser"]
        ReactUI[React Frontend<br/>TypeScript, Vite<br/>Port 3000]
    end
    
    subgraph Docker["Docker Environment"]
        API[FastAPI Backend<br/>Python 3.11<br/>Port 8080]
        
        PostgreSQL[(PostgreSQL<br/>Database<br/>Port 5432)]
        
        Redis[(Redis<br/>Cache & Queue<br/>Port 6379)]
        
        Tools[Forensic Tools<br/>Container<br/>Sparrow, Hawk,<br/>Loki, YARA]
    end
    
    subgraph FileSystem["Host File System"]
        Evidence[Evidence Storage<br/>~/forensics-evidence/]
        ToolsFS[Tools Directory<br/>/opt/forensics-tools/]
    end
    
    ReactUI -->|HTTPS/REST| API
    ReactUI -->|WebSocket| API
    
    API -->|Read/Write| PostgreSQL
    API -->|Cache/Pub-Sub| Redis
    API -->|Execute| Tools
    API -->|Store artifacts| Evidence
    
    Tools -->|Read tools| ToolsFS
    Tools -->|Write results| Evidence
    
    style ReactUI fill:#61dafb,stroke:#21a1c4,color:#000
    style API fill:#009688,stroke:#00796b,color:#fff
    style PostgreSQL fill:#336791,stroke:#2c5282,color:#fff
    style Redis fill:#dc382d,stroke:#a62518,color:#fff
    style Tools fill:#ff9800,stroke:#f57c00,color:#fff
```

---

## 3. Component Diagram - Backend API (Level 3)

Shows the internal structure of the FastAPI backend.

```mermaid
graph TB
    subgraph API["FastAPI Application"]
        Main[main.py<br/>Entry Point<br/>CORS, Lifespan]
        
        subgraph Routes["API Routes /api/v1"]
            CasesR[Cases Router<br/>CRUD operations]
            M365R[M365 Router<br/>Sparrow, Hawk]
            CredsR[Credentials Router<br/>HIBP, Dehashed]
            EndpointR[Endpoint Router<br/>Loki, YARA]
        end
        
        subgraph Services["Business Logic"]
            CasesS[Case Service]
            M365S[M365 Service]
            CredsS[Credentials Service]
            EndpointS[Endpoint Service]
        end
        
        subgraph Middleware["Middleware Stack"]
            Auth[Authentication<br/>API Key Validation]
            RBAC[RBAC Middleware<br/>Permission Checks]
            CaseCtx[Case Context<br/>case_id Validation]
            Deprec[Deprecation<br/>Route Tracking]
        end
        
        subgraph Models["Data Models"]
            CaseM[Case Model]
            InvestM[Investigation Model]
            UserM[User Model]
        end
    end
    
    Main --> Routes
    Routes --> Services
    Services --> Models
    
    Main --> Middleware
    Middleware --> Routes
    
    style Main fill:#1e88e5,stroke:#1565c0,color:#fff
    style Routes fill:#4caf50,stroke:#388e3c,color:#fff
    style Services fill:#ff9800,stroke:#f57c00,color:#fff
    style Middleware fill:#9c27b0,stroke:#7b1fa2,color:#fff
    style Models fill:#f44336,stroke:#d32f2f,color:#fff
```

---

## 4. Component Diagram - React Frontend (Level 3)

Shows the internal structure of the React application.

```mermaid
graph TB
    subgraph Frontend["React Application"]
        App[App.tsx<br/>Root Component<br/>Router Setup]
        
        subgraph Pages["Pages"]
            Dashboard[Dashboard]
            Cases[Cases List]
            CaseDetail[Case Detail]
            Investigation[Investigation]
            Reports[Reports]
        end
        
        subgraph Components["Reusable Components"]
            CaseCard[Case Card]
            Timeline[Timeline]
            Graph[Network Graph]
            DataTable[Data Table]
            Modal[Modal Dialog]
        end
        
        subgraph State["State Management"]
            Store[Redux Store]
            CaseSlice[Case Slice]
            AuthSlice[Auth Slice]
            UISlice[UI Slice]
        end
        
        subgraph Services["API Services"]
            CaseAPI[Case API]
            M365API[M365 API]
            CredsAPI[Credentials API]
        end
        
        subgraph Hooks["Custom Hooks"]
            UseCases[useCases]
            UseAuth[useAuth]
            UseWebSocket[useWebSocket]
        end
    end
    
    App --> Pages
    Pages --> Components
    Pages --> Hooks
    Hooks --> Services
    Hooks --> State
    Components --> State
    
    style App fill:#61dafb,stroke:#21a1c4,color:#000
    style Pages fill:#4caf50,stroke:#388e3c,color:#fff
    style Components fill:#ff9800,stroke:#f57c00,color:#fff
    style State fill:#9c27b0,stroke:#7b1fa2,color:#fff
    style Services fill:#f44336,stroke:#d32f2f,color:#fff
    style Hooks fill:#00bcd4,stroke:#0097a7,color:#fff
```

---

## 5. Deployment Diagram

Shows how the system is deployed with Docker.

```mermaid
graph TB
    subgraph Host["Linux Host (Kali/Ubuntu/WSL2)"]
        subgraph Docker["Docker Compose"]
            NGINX[NGINX<br/>Reverse Proxy<br/>Port 80/443]
            
            API[mcp-forensics<br/>FastAPI Container<br/>Port 8080]
            
            Frontend[frontend-react<br/>Nginx Static Server<br/>Port 3000]
            
            DB[(PostgreSQL<br/>Container<br/>Port 5432)]
            
            Cache[(Redis<br/>Container<br/>Port 6379)]
        end
        
        subgraph HostFS["Host File System"]
            Evidence[/var/evidence/<br/>Case Artifacts]
            Tools[/opt/forensics-tools/<br/>Mounted Tools]
            Logs[/var/log/forensics/<br/>Application Logs]
        end
        
        subgraph Network["Docker Network: forensics-net"]
        end
    end
    
    User[Users] -->|HTTPS:443| NGINX
    NGINX -->|Proxy| API
    NGINX -->|Serve| Frontend
    
    Frontend -.->|API Calls| API
    API -->|Query| DB
    API -->|Cache| Cache
    API -->|Read/Write| Evidence
    API -->|Execute| Tools
    API -->|Write| Logs
    
    API -.-> Network
    DB -.-> Network
    Cache -.-> Network
    Frontend -.-> Network
    
    style Host fill:#e0e0e0,stroke:#9e9e9e
    style Docker fill:#2196f3,stroke:#1976d2
    style NGINX fill:#009688,stroke:#00796b,color:#fff
    style API fill:#4caf50,stroke:#388e3c,color:#fff
    style Frontend fill:#61dafb,stroke:#21a1c4,color:#000
    style DB fill:#336791,stroke:#2c5282,color:#fff
    style Cache fill:#dc382d,stroke:#a62518,color:#fff
```

---

## 6. Data Flow Diagram - M365 Analysis

Shows the flow of data during an M365 forensic analysis.

```mermaid
sequenceDiagram
    actor User as SOC Analyst
    participant UI as React Frontend
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant Tools as Forensic Tools
    participant M365 as Microsoft 365
    participant FS as File System
    
    User->>UI: Start M365 Analysis
    UI->>API: POST /api/v1/m365/analyze<br/>+ X-Case-ID header
    
    API->>API: Validate case_id<br/>(Case Context Middleware)
    API->>API: Check permissions<br/>(RBAC Middleware)
    
    API->>DB: Create investigation record
    DB-->>API: investigation_id
    
    API->>Tools: Execute Sparrow.ps1<br/>(async subprocess)
    activate Tools
    
    Tools->>M365: Collect audit logs<br/>(Graph API)
    M365-->>Tools: Audit log data
    
    Tools->>M365: Analyze sign-ins
    M365-->>Tools: Sign-in data
    
    Tools->>FS: Save CSV results
    Tools-->>API: Execution complete
    deactivate Tools
    
    API->>API: Parse CSV results
    API->>DB: Update investigation<br/>with results
    
    API-->>UI: WebSocket: Status update
    UI-->>User: Display results
    
    User->>UI: View detailed results
    UI->>API: GET /api/v1/cases/{id}
    API->>DB: Query case data
    DB-->>API: Case + investigations
    API-->>UI: JSON response
    UI-->>User: Render timeline
```

---

## 7. Security Architecture

Shows the security layers and controls.

```mermaid
graph TB
    subgraph Internet["Internet"]
        Attacker[Potential Attacker]
    end
    
    subgraph Perimeter["Perimeter Security"]
        Firewall[Firewall<br/>iptables]
        WAF[Web Application Firewall]
    end
    
    subgraph Application["Application Layer"]
        HTTPS[TLS/HTTPS<br/>SSL Certificates]
        
        subgraph Auth["Authentication & Authorization"]
            APIKey[API Key Validation]
            RBAC[Role-Based Access Control]
            RateLimit[Rate Limiting]
        end
        
        subgraph Validation["Input Validation"]
            Sanitize[Input Sanitization]
            CSRF[CSRF Protection]
            CaseCtx[Case Context Validation]
        end
        
        subgraph Audit["Audit & Monitoring"]
            Logging[Audit Logging]
            Alerts[Security Alerts]
            Monitoring[Real-time Monitoring]
        end
    end
    
    subgraph Data["Data Layer"]
        Encryption[Data Encryption at Rest]
        Backup[Encrypted Backups]
        Access[Least Privilege Access]
    end
    
    subgraph Forensics["Forensic Tools"]
        Sandbox[Sandboxed Execution]
        ReadOnly[Read-only Tool Access]
        Isolation[Process Isolation]
    end
    
    Attacker -->|Blocked| Firewall
    Firewall --> WAF
    WAF --> HTTPS
    HTTPS --> Auth
    Auth --> Validation
    Validation --> Audit
    Audit --> Data
    Data --> Forensics
    
    style Attacker fill:#f44336,stroke:#d32f2f,color:#fff
    style Firewall fill:#ff9800,stroke:#f57c00,color:#fff
    style Auth fill:#4caf50,stroke:#388e3c,color:#fff
    style Validation fill:#2196f3,stroke:#1976d2,color:#fff
    style Audit fill:#9c27b0,stroke:#7b1fa2,color:#fff
    style Data fill:#009688,stroke:#00796b,color:#fff
    style Forensics fill:#607d8b,stroke:#455a64,color:#fff
```

---

## 8. Database Schema (Entity Relationship)

Shows the main database entities and relationships.

```mermaid
erDiagram
    USERS ||--o{ CASES : creates
    USERS ||--o{ INVESTIGATIONS : executes
    CASES ||--|{ INVESTIGATIONS : contains
    CASES ||--o{ TIMELINE_EVENTS : has
    INVESTIGATIONS ||--o{ RESULTS : produces
    CASES ||--o{ ARTIFACTS : stores
    
    USERS {
        uuid id PK
        string username UK
        string email UK
        string password_hash
        string role
        jsonb permissions
        timestamp created_at
        timestamp last_login
    }
    
    CASES {
        string case_id PK
        string name
        text description
        string status
        string priority
        uuid created_by FK
        uuid assigned_to FK
        timestamp created_at
        timestamp updated_at
    }
    
    INVESTIGATIONS {
        uuid id PK
        string case_id FK
        string type
        string status
        jsonb config
        jsonb results
        uuid executed_by FK
        timestamp started_at
        timestamp completed_at
    }
    
    TIMELINE_EVENTS {
        uuid id PK
        string case_id FK
        timestamp event_time
        string event_type
        string source
        jsonb data
        timestamp created_at
    }
    
    RESULTS {
        uuid id PK
        uuid investigation_id FK
        string result_type
        jsonb data
        string file_path
        timestamp created_at
    }
    
    ARTIFACTS {
        uuid id PK
        string case_id FK
        string artifact_type
        string file_path
        bigint file_size
        string hash_sha256
        jsonb metadata
        timestamp created_at
    }
```

---

## 9. Network Topology

Shows the network architecture.

```mermaid
graph TB
    subgraph Public["Public Internet"]
        Client[Client Browser]
    end
    
    subgraph DMZ["DMZ Network (172.20.0.0/24)"]
        LB[Load Balancer<br/>172.20.0.10]
        NGINX[NGINX Reverse Proxy<br/>172.20.0.20]
    end
    
    subgraph AppNetwork["Application Network (172.21.0.0/24)"]
        API1[API Server 1<br/>172.21.0.30]
        API2[API Server 2<br/>172.21.0.31]
        Frontend[Frontend Server<br/>172.21.0.40]
    end
    
    subgraph DataNetwork["Data Network (172.22.0.0/24)"]
        DB1[(Primary DB<br/>172.22.0.50)]
        DB2[(Replica DB<br/>172.22.0.51)]
        Redis1[Redis Master<br/>172.22.0.60]
        Redis2[Redis Replica<br/>172.22.0.61]
    end
    
    subgraph ToolsNetwork["Tools Network (172.23.0.0/24)"]
        Tools[Forensic Tools<br/>172.23.0.70]
    end
    
    Client -->|HTTPS:443| LB
    LB --> NGINX
    NGINX --> API1
    NGINX --> API2
    NGINX --> Frontend
    
    API1 --> DB1
    API2 --> DB1
    DB1 -.->|Replication| DB2
    
    API1 --> Redis1
    API2 --> Redis1
    Redis1 -.->|Replication| Redis2
    
    API1 --> Tools
    API2 --> Tools
    
    style Public fill:#e0e0e0,stroke:#9e9e9e
    style DMZ fill:#fff3e0,stroke:#ff9800
    style AppNetwork fill:#e8f5e9,stroke:#4caf50
    style DataNetwork fill:#e3f2fd,stroke:#2196f3
    style ToolsNetwork fill:#f3e5f5,stroke:#9c27b0
```

---

## 10. CI/CD Pipeline

Shows the automated deployment pipeline.

```mermaid
graph LR
    subgraph Development["Development"]
        Dev[Developer]
        Git[Git Push]
    end
    
    subgraph GitHub["GitHub"]
        PR[Pull Request]
        Main[Main Branch]
    end
    
    subgraph CI["Continuous Integration"]
        Lint[Linting<br/>Ruff, ESLint]
        Test[Testing<br/>pytest, vitest]
        Build[Build<br/>Docker Images]
        Security[Security Scan<br/>Trivy, Safety]
    end
    
    subgraph Quality["Quality Gates"]
        Coverage[Coverage > 60%]
        NoVuln[No Critical Vulns]
        Approval[Manual Approval]
    end
    
    subgraph CD["Continuous Deployment"]
        Staging[Deploy to Staging]
        StagingTest[Integration Tests]
        Production[Deploy to Production]
    end
    
    Dev --> Git
    Git --> PR
    PR --> Lint
    Lint --> Test
    Test --> Build
    Build --> Security
    Security --> Coverage
    Coverage --> NoVuln
    NoVuln --> Approval
    Approval --> Staging
    Staging --> StagingTest
    StagingTest --> Production
    
    PR -.->|Merge| Main
    Main --> Production
    
    style Development fill:#4caf50,stroke:#388e3c,color:#fff
    style GitHub fill:#24292e,stroke:#000,color:#fff
    style CI fill:#2196f3,stroke:#1976d2,color:#fff
    style Quality fill:#ff9800,stroke:#f57c00,color:#fff
    style CD fill:#9c27b0,stroke:#7b1fa2,color:#fff
```

---

## 📖 Diagram Rendering

These diagrams use Mermaid syntax and can be rendered in:

- **GitHub**: Automatically rendered in markdown
- **VS Code**: Install "Markdown Preview Mermaid Support" extension
- **Documentation Sites**: Mkdocs, Docusaurus, GitBook
- **Online**: [Mermaid Live Editor](https://mermaid.live/)

---

**Last Updated:** December 16, 2024  
**Version:** 1.0  
**Format:** Mermaid + C4 Model
