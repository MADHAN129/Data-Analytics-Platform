# Agentic Analytics Platform for Enterprise Applications Using MCP and Multi-Agent AI

## Project Plan Document
**Version:** 1.0  
**Date:** July 11, 2026  
**Status:** Draft  
**Classification:** Internal - Confidential

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Architecture Overview](#2-project-architecture-overview)
3. [Technology Stack Details](#3-technology-stack-details)
4. [Module Breakdown](#4-module-breakdown)
5. [Database Schema for Metadata Storage](#5-database-schema-for-metadata-storage)
6. [API Endpoints Design](#6-api-endpoints-design)
7. [Agent Workflow Diagrams](#7-agent-workflow-diagrams)
8. [Implementation Phases and Milestones](#8-implementation-phases-and-milestones)
9. [Testing Strategy](#9-testing-strategy)
10. [Deployment Considerations](#10-deployment-considerations)
11. [Risk Assessment and Mitigation](#11-risk-assessment-and-mitigation)
12. [Appendices](#12-appendices)

---

## 1. Executive Summary

### 1.1 Project Vision

The Agentic Analytics Platform is an enterprise-grade, AI-powered analytics solution that enables natural language interaction with business data across ERP, CRM, HRMS, E-Commerce, Data Warehouses, and Custom Database systems. The platform leverages the Model Context Protocol (MCP) and Multi-Agent AI architecture to provide intuitive data querying, visualization, and predictive analytics capabilities.

### 1.2 Business Objectives

- **Democratize Data Access**: Enable non-technical stakeholders to query complex enterprise databases using natural language
- **Accelerate Decision Making**: Provide real-time insights through auto-generated dashboards and predictive analytics
- **Reduce IT Dependency**: Eliminate the bottleneck of report generation and data extraction requests
- **Ensure Enterprise Security**: Implement advanced RBAC and data governance across all connected systems
- **Universal Integration**: Support all major enterprise systems through a unified MCP-based architecture

### 1.3 Key Differentiators

| Feature | Capability |
|---------|------------|
| Natural Language Querying | English-to-SQL translation with context awareness |
| Voice Commands | Real-time speech-to-text and text-to-speech interaction |
| Auto Dashboard Generation | AI-powered visualization recommendation and creation |
| Multi-Database Support | Unified interface via MCP servers for any database |
| Conversational Follow-ups | Context-aware multi-turn conversations |
| Root Cause Analysis | AI-driven anomaly investigation and correlation |
| Predictive Analytics | Time-series forecasting and trend analysis |
| Export Options | PDF, Excel, PNG export for reports and visualizations |

---

## 2. Project Architecture Overview

### 2.1 High-Level Architecture

`
+===========================================================================+
|                           CLIENT LAYER                                     |
+===========================================================================+
|  Web Application (React/Next.js)  |  Mobile App (React Native)            |
|  Voice Interface (WebSocket)      |  API Consumers (REST/GraphQL)         |
+===========================================================================+
                                      |
                                      v
+===========================================================================+
|                         API GATEWAY LAYER                                  |
+===========================================================================+
|  Kong/AWS API Gateway  |  Authentication (JWT/OAuth2)  |  Rate Limiting   |
|  Request Routing       |  Load Balancing               |  Caching         |
+===========================================================================+
                                      |
                                      v
+===========================================================================+
|                      APPLICATION SERVER LAYER                              |
+===========================================================================+
|  FastAPI Backend Server                                                      |
|  +------------------+  +------------------+  +------------------+           |
|  | Query Service    |  | Dashboard Svc    |  | Export Service   |           |
|  +------------------+  +------------------+  +------------------+           |
|  +------------------+  +------------------+  +------------------+           |
|  | User/Auth Svc    |  | Anomaly Svc      |  | Predictive Svc   |           |
|  +------------------+  +------------------+  +------------------+           |
|  +------------------+  +------------------+                                 |
|  | CSV Import Svc   |  | API Integration  |                                 |
|  +------------------+  +------------------+                                 |
+===========================================================================+
                                      |
                                      v
+===========================================================================+
|                       AI AGENT ORCHESTRATION LAYER                         |
+===========================================================================+
|  Agent Orchestrator (LangGraph)                                            |
|  +------------------+  +------------------+  +------------------+           |
|  | Query Agent      |  | Analysis Agent   |  | Visualization    |           |
|  | (SQL Generation) |  | (Root Cause)     |  | Agent            |           |
|  +------------------+  +------------------+  +------------------+           |
|  +------------------+  +------------------+  +------------------+           |
|  | Predictive Agent |  | Voice Agent      |  | Anomaly Agent    |           |
|  +------------------+  +------------------+  +------------------+           |
+===========================================================================+
                                      |
                                      v
+===========================================================================+
|                      MCP SERVER LAYER (Model Context Protocol)             |
+===========================================================================+
|  +--------------+  +--------------+  +--------------+  +--------------+     |
|  | MCP Server   |  | MCP Server   |  | MCP Server   |  | MCP Server   |   |
|  | (PostgreSQL) |  | (MySQL)      |  | (SQL Server) |  | (MongoDB)    |   |
|  +--------------+  +--------------+  +--------------+  +--------------+     |
|  +--------------+  +--------------+  +--------------+  +--------------+     |
|  | MCP Server   |  | MCP Server   |  | MCP Server   |  | MCP Server   |   |
|  | (Oracle)     |  | (Snowflake)  |  | (BigQuery)   |  | (REST API)   |   |
|  +--------------+  +--------------+  +--------------+  +--------------+     |
+===========================================================================+
                                      |
                                      v
+===========================================================================+
|                        AI MODEL INFERENCE LAYER                            |
+===========================================================================+
|  +------------------+  +------------------+  +------------------+           |
|  | Qwen3 8B LLM     |  | KittenTTS       |  | Whisper ASR      |           |
|  | (Query/Chat)     |  | (Voice Output)  |  | (Voice Input)    |           |
|  +------------------+  +------------------+  +------------------+           |
|  +------------------+  +------------------+                                 |
|  | Anomaly Detection |  | Forecasting     |                                 |
|  | (Isolation Forest)|  | (Prophet/LSTM)  |                                 |
|  +------------------+  +------------------+                                 |
+===========================================================================+
                                      |
                                      v
+===========================================================================+
|                         DATA STORAGE LAYER                                 |
+===========================================================================+
|  +------------------+  +------------------+  +------------------+           |
|  | PostgreSQL       |  | Redis            |  | MinIO/S3         |           |
|  | (Metadata/Config)|  | (Cache/Sessions) |  | (File Storage)   |           |
|  +------------------+  +------------------+  +------------------+           |
+===========================================================================+
`

### 2.2 Component Interaction Flow

`
User Input (Text/Voice)
        |
        v
[Voice Agent] <---> [Whisper ASR] <---> [Text Query]
        |
        v
[Query Agent] <---> [Qwen3 8B LLM] <---> [SQL Generation]
        |
        v
[Agent Orchestrator] <---> [MCP Protocol] <---> [MCP Server]
        |
        v
[Target Database] <--- Executes Query ---> [Results]
        |
        v
[Analysis Agent] <---> [Anomaly Detection] <---> [Root Cause Analysis]
        |
        v
[Visualization Agent] <---> [Auto Dashboard] <---> [Charts/Graphs]
        |
        v
[KittenTTS] <---> [Voice Output] <---> [User Response]
        |
        v
[Export Service] <---> [PDF/Excel/PNG] <---> [Download]
`

### 2.3 MCP Protocol Integration

The Model Context Protocol (MCP) serves as the universal bridge between the AI agents and target databases. Each database type has a dedicated MCP server that:

1. **Exposes database schema** as structured context for the LLM
2. **Translates natural language** queries into database-specific SQL
3. **Handles connection pooling** and query optimization
4. **Manages security** and access control at the database level
5. **Provides real-time schema updates** when database structure changes

---

## 3. Technology Stack Details

### 3.1 Frontend Stack

| Technology | Purpose | Version | Rationale |
|------------|---------|---------|-----------|
| **Next.js** | Web Application Framework | 15.x | SSR/SSG, API routes, React ecosystem |
| **React** | UI Component Library | 19.x | Component-based architecture |
| **TypeScript** | Type Safety | 5.x | Enterprise-grade code quality |
| **Tailwind CSS** | Styling | 3.x | Rapid UI development |
| **Recharts/D3.js** | Data Visualization | Latest | Interactive charts and graphs |
| **WebSocket** | Real-time Communication | Native | Voice streaming, live updates |
| **React Query** | Data Fetching | 5.x | Caching, optimistic updates |
| **Zustand** | State Management | 4.x | Lightweight global state |
| **React Hook Form** | Form Management | 7.x | CSV upload, query input |
| **Shadcn/ui** | UI Components | Latest | Accessible, customizable components |

### 3.2 Backend Stack

| Technology | Purpose | Version | Rationale |
|------------|---------|---------|-----------|
| **Python** | Primary Language | 3.11+ | AI/ML ecosystem, async support |
| **FastAPI** | Web Framework | 0.110+ | High performance, async, OpenAPI |
| **SQLAlchemy** | ORM | 2.0+ | Database-agnostic queries |
| **Alembic** | Database Migrations | Latest | Schema version control |
| **Celery** | Task Queue | 5.x | Async job processing |
| **Redis** | Cache/Pub-Sub | 7.x | Caching, session store, Celery broker |
| **Pydantic** | Data Validation | 2.x | Request/response validation |
| **Uvicorn** | ASGI Server | Latest | Production ASGI server |
| **Gunicorn** | Process Manager | 21.x | Multi-worker deployment |

### 3.3 AI/ML Stack

| Technology | Purpose | Version | Rationale |
|------------|---------|---------|-----------|
| **Qwen3 8B** | LLM (Primary) | 8B | SQL generation, conversation, reasoning |
| **HuggingFace Transformers** | Model Runtime | 4.x | Model loading, inference |
| **vLLM** | LLM Serving | Latest | High-throughput inference, batching |
| **KittenTTS** | Text-to-Speech | Latest | Lightweight, CPU-only, Apache 2.0 |
| **OpenAI Whisper** | Speech-to-Text | large-v3 | Accurate transcription |
| **LangGraph** | Agent Orchestration | 0.2+ | Multi-agent workflows, state management |
| **LangChain** | LLM Framework | 0.2+ | Chain composition, tool integration |
| **scikit-learn** | ML Utilities | 1.4+ | Anomaly detection (Isolation Forest) |
| **Prophet** | Time Series | Latest | Forecasting for predictive analytics |
| **pandas** | Data Processing | 2.x | Data manipulation, CSV processing |
| **NumPy** | Numerical Computing | Latest | Array operations |
| **PyOD** | Anomaly Detection | Latest | Advanced anomaly detection algorithms |

### 3.4 MCP Stack

| Technology | Purpose | Version | Rationale |
|------------|---------|---------|-----------|
| **MCP SDK (Python)** | MCP Implementation | Latest | Official MCP protocol support |
| **mcp-server-postgres** | PostgreSQL MCP | Latest | Native PostgreSQL integration |
| **mcp-server-mysql** | MySQL MCP | Latest | Native MySQL integration |
| **mcp-server-mssql** | SQL Server MCP | Latest | Microsoft SQL Server support |
| **mcp-server-mongodb** | MongoDB MCP | Latest | NoSQL document database support |
| **Custom MCP Servers** | Oracle, Snowflake, etc. | Custom | Extended database support |

### 3.5 Infrastructure Stack

| Technology | Purpose | Version | Rationale |
|------------|---------|---------|-----------|
| **Docker** | Containerization | 24.x | Consistent environments |
| **Kubernetes** | Orchestration | 1.29+ | Production-grade deployment |
| **Helm** | Package Management | 3.x | Kubernetes application packaging |
| **PostgreSQL** | Metadata Database | 16.x | Metadata, config, audit logs |
| **Redis** | Cache/Sessions | 7.x | Caching, real-time features |
| **MinIO/AWS S3** | Object Storage | Latest | File storage, exports |
| **Prometheus** | Metrics Collection | Latest | System monitoring |
| **Grafana** | Metrics Visualization | Latest | Operational dashboards |
| **ELK Stack** | Log Management | 8.x | Centralized logging |

---

## 4. Module Breakdown

### 4.1 Frontend Module

#### 4.1.1 Query Interface Module

**Components:**
- QueryInput - Natural language text input with auto-suggestions
- VoiceInput - Microphone button for voice command activation
- QueryHistory - Searchable list of previous queries with re-run capability
- QuerySuggestions - AI-powered query recommendations based on context
- SQLPreview - Display of generated SQL for transparency

**Features:**
- Real-time query validation and suggestions
- Syntax highlighting for SQL preview
- Multi-language support for query input
- Query template library for common analytics patterns
- Keyboard shortcuts for power users

#### 4.1.2 Dashboard Module

**Components:**
- DashboardGrid - Responsive grid layout for widgets
- ChartWidget - Auto-configured chart based on data type
- TableWidget - Interactive data table with sorting/filtering
- KPIWidget - Key performance indicator cards
- FilterBar - Global filters for dashboard context
- DashboardSelector - Template and saved dashboard browser

**Features:**
- Drag-and-drop widget arrangement
- Auto-refresh on data updates
- Responsive design for all screen sizes
- Dashboard sharing and embedding
- Custom theme support

#### 4.1.3 Voice Interface Module

**Components:**
- VoiceRecorder - Microphone capture with visual feedback
- VoiceWaveform - Real-time audio visualization
- TTSSettings - Voice output configuration
- VoiceCommandDisplay - Transcribed text display

**Features:**
- Push-to-talk and hands-free modes
- Noise cancellation and echo suppression
- Multiple voice profiles for TTS output
- Voice command history and learning
- Accessibility-first design

#### 4.1.4 Export Module

**Components:**
- ExportDialog - Format selection and configuration
- PDFExporter - Report generation with branding
- ExcelExporter - Data export with formatting
- ImageExporter - Dashboard/chart screenshot
- ScheduledExport - Recurring export configuration

**Features:**
- One-click export from any view
- Custom report templates
- Batch export for multiple dashboards
- Email delivery integration
- Watermark and branding options

### 4.2 Backend Module

#### 4.2.1 Query Processing Service

**Endpoints:**
- POST /api/v1/queries/execute - Execute natural language query
- POST /api/v1/queries/sql - Execute raw SQL (admin only)
- GET /api/v1/queries/history - Query execution history
- GET /api/v1/queries/{id}/status - Async query status
- POST /api/v1/queries/{id}/follow-up - Conversational follow-up

**Responsibilities:**
- Natural language to SQL translation via Qwen3 8B
- Query validation and sanitization
- Execution plan optimization
- Result caching and memoization
- Query performance monitoring

#### 4.2.2 Dashboard Service

**Endpoints:**
- POST /api/v1/dashboards - Create dashboard
- GET /api/v1/dashboards - List dashboards
- GET /api/v1/dashboards/{id} - Get dashboard details
- PUT /api/v1/dashboards/{id} - Update dashboard
- DELETE /api/v1/dashboards/{id} - Delete dashboard
- POST /api/v1/dashboards/auto-generate - AI-powered generation
- POST /api/v1/dashboards/{id}/widgets - Add widget
- GET /api/v1/dashboards/{id}/export - Export dashboard

**Responsibilities:**
- Dashboard CRUD operations
- Widget configuration and layout management
- Auto-generation from query results
- Dashboard templates and themes
- Sharing and access control

#### 4.2.3 Anomaly Detection Service

**Endpoints:**
- POST /api/v1/anomaly/detect - Run anomaly detection
- GET /api/v1/anomaly/alerts - Get active alerts
- PUT /api/v1/anomaly/alerts/{id}/acknowledge - Acknowledge alert
- POST /api/v1/anomaly/configure - Configure detection parameters
- GET /api/v1/anomaly/history - Historical anomaly data

**Responsibilities:**
- Real-time anomaly detection using Isolation Forest, Z-score, IQR
- Configurable sensitivity and thresholds
- Alert notification (email, webhook, in-app)
- Root cause analysis via AI correlation
- Anomaly pattern learning over time

#### 4.2.4 Predictive Analytics Service

**Endpoints:**
- POST /api/v1/predictions/forecast - Generate forecast
- GET /api/v1/predictions/models - List available models
- POST /api/v1/predictions/train - Train custom model
- GET /api/v1/predictions/{id} - Get prediction results
- PUT /api/v1/predictions/{id}/accuracy - Log actual vs predicted

**Responsibilities:**
- Time-series forecasting (Prophet, LSTM, ARIMA)
- Trend analysis and pattern recognition
- Model selection and auto-tuning
- Accuracy tracking and model retraining
- Confidence interval calculation

#### 4.2.5 User and Authentication Service

**Endpoints:**
- POST /api/v1/auth/login - User login
- POST /api/v1/auth/refresh - Token refresh
- POST /api/v1/auth/logout - User logout
- GET /api/v1/users/me - Current user profile
- PUT /api/v1/users/me - Update profile
- POST /api/v1/users - Create user (admin)
- GET /api/v1/users - List users (admin)
- GET /api/v1/roles - List roles
- POST /api/v1/roles - Create role (admin)
- PUT /api/v1/roles/{id}/permissions - Update role permissions

**Responsibilities:**
- JWT-based authentication
- OAuth2/OIDC integration (Azure AD, Okta, Google)
- Advanced RBAC with granular permissions
- Session management and audit logging
- Multi-factor authentication support

#### 4.2.6 CSV Import Service

**Endpoints:**
- POST /api/v1/import/csv/upload - Upload CSV file
- POST /api/v1/import/csv/{id}/validate - Validate CSV data
- POST /api/v1/import/csv/{id}/import - Execute import
- GET /api/v1/import/csv/{id}/status - Import status
- GET /api/v1/import/history - Import history

**Responsibilities:**
- File upload and storage
- Schema inference from CSV headers
- Data validation and type detection
- Duplicate detection and handling
- Incremental and full import modes
### 4.3 MCP Server Module

#### 4.3.1 PostgreSQL MCP Server

**Responsibilities:**
- Schema introspection and context generation
- SQL query execution with parameterization
- Connection pooling and management
- Query result formatting for LLM consumption
- Schema change detection and notification

#### 4.3.2 MySQL MCP Server

**Responsibilities:**
- MySQL-specific SQL dialect handling
- Stored procedure support
- Replication-aware query routing
- Charset and collation management
- MySQL-specific optimizations

#### 4.3.3 SQL Server MCP Server

**Responsibilities:**
- T-SQL translation and execution
- Azure SQL compatibility
- Linked server query support
- SQL Server-specific features (CTE, Window functions)
- Integration with Active Directory

#### 4.3.4 MongoDB MCP Server

**Responsibilities:**
- NoSQL to SQL translation layer
- Aggregation pipeline generation
- Document schema inference
- Index-aware query optimization
- BSON type handling

#### 4.3.5 Custom Database MCP Server (Base)

**Responsibilities:**
- Abstract base class for custom MCP servers
- Database adapter pattern implementation
- Connection configuration management
- Query validation and sanitization
- Result formatting standardization


### 4.4 AI Agent Module

#### 4.4.1 Query Agent

**Model:** Qwen3 8B
**Responsibilities:**
- Natural language understanding and intent extraction
- Schema-aware SQL generation
- Query optimization suggestions
- Multi-step query decomposition
- Context-aware follow-up query generation

**Tools:**
- execute_sql - Execute generated SQL via MCP
- get_schema - Retrieve database schema
- validate_sql - Syntax and semantic validation
- explain_query - Generate human-readable query explanation
- suggest_indexes - Recommend query optimizations

#### 4.4.2 Analysis Agent

**Model:** Qwen3 8B
**Responsibilities:**
- Anomaly investigation and root cause analysis
- Statistical analysis of query results
- Trend identification and pattern recognition
- Correlation analysis across datasets
- Natural language insight generation

**Tools:**
- calculate_statistics - Compute statistical measures
- detect_anomalies - Run anomaly detection algorithms
- analyze_trends - Identify trends and patterns
- correlate_data - Cross-dataset correlation
- generate_insights - Create natural language insights

#### 4.4.3 Visualization Agent

**Model:** Qwen3 8B
**Responsibilities:**
- Chart type recommendation based on data characteristics
- Dashboard layout optimization
- Color scheme and accessibility compliance
- Responsive design suggestions
- Chart configuration generation

**Tools:**
- recommend_chart - Suggest optimal chart type
- generate_config - Create chart configuration
- validate_visualization - Check accessibility and clarity
- optimize_layout - Dashboard layout recommendations
- create_widget - Generate widget from query results

#### 4.4.4 Voice Agent

**Models:** Whisper ASR + KittenTTS
**Responsibilities:**
- Speech-to-text transcription
- Voice command interpretation
- Text-to-speech output generation
- Voice profile management
- Multi-language voice support

**Tools:**
- transcribe_audio - Convert speech to text
- synthesize_speech - Convert text to speech
- detect_language - Identify spoken language
- manage_voice_profiles - Voice profile operations
- process_voice_command - Voice command routing

#### 4.4.5 Anomaly Agent

**Model:** Qwen3 8B + scikit-learn
**Responsibilities:**
- Real-time anomaly monitoring
- Multi-dimensional anomaly detection
- Alert generation and escalation
- Anomaly clustering and categorization
- Historical anomaly pattern analysis

**Tools:**
- run_detection - Execute anomaly detection
- calculate_thresholds - Dynamic threshold adjustment
- cluster_anomalies - Group related anomalies
- generate_alert - Create notification
- investigate_cause - Root cause analysis

#### 4.4.6 Predictive Agent

**Model:** Qwen3 8B + Prophet/LSTM
**Responsibilities:**
- Forecast generation and validation
- Model selection and hyperparameter tuning
- Prediction accuracy tracking
- Seasonal pattern recognition
- Anomaly-aware forecasting

**Tools:**
- generate_forecast - Create time-series forecast
- evaluate_model - Model performance metrics
- tune_hyperparameters - Auto-tune model parameters
- detect_seasonality - Identify seasonal patterns
- compare_models - Benchmark multiple models

#### 4.4.7 Agent Orchestrator

**Model:** Qwen3 8B (Supervisor)
**Framework:** LangGraph
**Responsibilities:**
- Multi-agent coordination and routing
- State management across agent interactions
- Error handling and recovery
- Performance monitoring and optimization
- Conversation context management

---

## 5. Database Schema for Metadata Storage

### 5.1 Entity Relationship Diagram

`
+------------------+       +------------------+       +------------------+
|     users        |       |      roles       |       |  permissions     |
+------------------+       +------------------+       +------------------+
| id (PK)          |<----->| id (PK)          |<----->| id (PK)          |
| email            |       | name             |       | name             |
| password_hash    |       | description      |       | resource         |
| full_name        |       | created_at       |       | action           |
| avatar_url       |       | updated_at       |       | created_at       |
| auth_provider    |       +------------------+       +------------------+
| auth_provider_id |
| is_active        |       +------------------+       +------------------+
| mfa_enabled      |       |  role_permissions|       |   databases      |
| created_at       |       +------------------+       +------------------+
| updated_at       |       | role_id (FK)     |       | id (PK)          |
+------------------+       | permission_id(FK)|       | name             |
         |                 +------------------+       | type (enum)      |
         |                                            | connection_config|
         v                                            | schema_cache     |
+------------------+                                 | is_active        |
|  user_roles      |                                 | created_by (FK)  |
+------------------+                                 | created_at       |
| user_id (FK)     |                                 | updated_at       |
| role_id (FK)     |                                 +------------------+
| assigned_at      |                                          |
| assigned_by (FK) |                                          v
+------------------+       +------------------+       +------------------+
|    queries       |       |   query_logs     |       |  dashboards      |
+------------------+       +------------------+       +------------------+
| id (PK)          |       | id (PK)          |       | id (PK)          |
| user_id (FK)     |       | query_id (FK)    |       | user_id (FK)     |
| database_id (FK) |       | execution_time_ms|       | title            |
| natural_language |       | rows_returned    |       | description      |
| generated_sql    |       | status           |       | layout_config    |
| status           |       | error_message    |       | is_template      |
| result_cache_key |       | executed_at      |       | is_public        |
| execution_time_ms|       | executed_by (FK) |       | auto_generated   |
| created_at       |       | connection_info  |       | created_at       |
| updated_at       |       +------------------+       | updated_at       |
+------------------+                                  +------------------+
         |                                                    |
         v                                                    v
+------------------+       +------------------+       +------------------+
|    widgets       |       |  query_filters   |       |  dashboards      |
+------------------+       +------------------+       |  _filters        |
| id (PK)          |       | id (PK)          |       +------------------+
| dashboard_id(FK) |       | query_id (FK)    |       | dashboard_id(FK) |
| query_id (FK)    |       | filter_name      |       | filter_id (FK)   |
| widget_type      |       | filter_type      |       +------------------+
| title            |       | default_value    |
| position_x       |       | is_required      |       +------------------+
| position_y       |       | options          |       |  conversations   |
| width            |       | created_at       |       +------------------+
| height           |       +------------------+       | id (PK)          |
| config           |                                  | user_id (FK)     |
| refresh_interval |                                  | title            |
| created_at       |                                  | database_id (FK) |
| updated_at       |                                  | context          |
+------------------+                                  | created_at       |
                                                      | updated_at       |
+------------------+       +------------------+       +------------------+
| conversation     |       | conversation     |       |  exports         |
| _messages        |       | _context         |       +------------------+
+------------------+       +------------------+       | id (PK)          |
| id (PK)          |       | id (PK)          |       | user_id (FK)     |
| conversation_id  |       | conversation_id  |       | dashboard_id(FK) |
| role (enum)      |       | key              |       | query_id (FK)    |
| content          |       | value            |       | export_type      |
| tool_calls       |       | expires_at       |       | file_path        |
| tokens_used      |       | created_at       |       | status           |
| created_at       |       +------------------+       | requested_at     |
+------------------+                                  | completed_at     |
                                                      +------------------+
+------------------+       +------------------+
|   anomalies      |       |   predictions    |
+------------------+       +------------------+
| id (PK)          |       | id (PK)          |
| database_id (FK) |       | database_id (FK) |
| table_name       |       | table_name       |
| column_name      |       | column_name      |
| anomaly_type     |       | model_type       |
| severity         |       | forecast_horizon |
| detected_value   |       | forecast_data    |
| expected_range   |       | confidence_level |
| context_data     |       | accuracy_score   |
| is_resolved      |       | trained_at       |
| resolved_by (FK) |       | created_at       |
| resolved_at      |       | expires_at       |
| created_at       |       +------------------+
+------------------+

+------------------+       +------------------+
|   audit_logs     |       |    api_keys      |
+------------------+       +------------------+
| id (PK)          |       | id (PK)          |
| user_id (FK)     |       | user_id (FK)     |
| action           |       | name             |
| resource_type    |       | key_hash         |
| resource_id      |       | permissions      |
| details (JSONB)  |       | expires_at       |
| ip_address       |       | last_used_at     |
| user_agent       |       | is_active        |
| created_at       |       | created_at       |
+------------------+       +------------------+

+------------------+       +------------------+
|   csv_imports    |       |   integrations   |
+------------------+       +------------------+
| id (PK)          |       | id (PK)          |
| user_id (FK)     |       | user_id (FK)     |
| file_name        |       | name             |
| file_path        |       | type             |
| file_size        |       | config           |
| row_count        |       | auth_config      |
| status           |       | status           |
| validation_errors|       | last_sync_at     |
| imported_to      |       | sync_frequency   |
| created_at       |       | created_at       |
| completed_at     |       | updated_at       |
+------------------+       +------------------+

+------------------+
|   notifications  |
+------------------+
| id (PK)          |
| user_id (FK)     |
| type             |
| title            |
| message          |
| data (JSONB)     |
| is_read          |
| created_at       |
+------------------+
`

### 5.2 Detailed Table Definitions

#### 5.2.1 Users Table

`sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(255) NOT NULL,
    avatar_url TEXT,
    auth_provider VARCHAR(50) DEFAULT 'local',
    auth_provider_id VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_auth_provider ON users(auth_provider, auth_provider_id);
`

#### 5.2.2 Roles Table

`sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Predefined roles
INSERT INTO roles (name, description, is_system) VALUES
    ('admin', 'Full system access', TRUE),
    ('analyst', 'Can create queries and dashboards', TRUE),
    ('viewer', 'Read-only access to dashboards', TRUE),
    ('data_manager', 'Can manage databases and imports', TRUE);
`

#### 5.2.3 Permissions Table

`sql
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(resource, action)
);

-- Granular permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('query:create', 'query', 'create', 'Create new queries'),
    ('query:execute', 'query', 'execute', 'Execute queries'),
    ('query:read', 'query', 'read', 'View query results'),
    ('dashboard:create', 'dashboard', 'create', 'Create dashboards'),
    ('dashboard:read', 'dashboard', 'read', 'View dashboards'),
    ('dashboard:update', 'dashboard', 'update', 'Edit dashboards'),
    ('dashboard:delete', 'dashboard', 'delete', 'Delete dashboards'),
    ('dashboard:share', 'dashboard', 'share', 'Share dashboards'),
    ('database:connect', 'database', 'connect', 'Connect to databases'),
    ('database:read_schema', 'database', 'read_schema', 'View database schema'),
    ('anomaly:read', 'anomaly', 'read', 'View anomalies'),
    ('anomaly:configure', 'anomaly', 'configure', 'Configure anomaly detection'),
    ('prediction:create', 'prediction', 'create', 'Create predictions'),
    ('prediction:read', 'prediction', 'read', 'View predictions'),
    ('import:csv', 'import', 'csv', 'Import CSV files'),
    ('export:pdf', 'export', 'pdf', 'Export to PDF'),
    ('export:excel', 'export', 'excel', 'Export to Excel'),
    ('export:png', 'export', 'png', 'Export to PNG'),
    ('user:manage', 'user', 'manage', 'Manage users'),
    ('role:manage', 'role', 'manage', 'Manage roles'),
    ('api_key:manage', 'api_key', 'manage', 'Manage API keys'),
    ('integration:manage', 'integration', 'manage', 'Manage integrations'),
    ('audit:read', 'audit', 'read', 'View audit logs');
`

#### 5.2.4 Databases Table

`sql
CREATE TABLE databases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN (
        'postgresql', 'mysql', 'sqlserver', 'mongodb',
        'oracle', 'snowflake', 'bigquery', 'sqlite', 'custom'
    )),
    host VARCHAR(255),
    port INTEGER,
    database_name VARCHAR(255),
    schema_name VARCHAR(255) DEFAULT 'public',
    connection_config JSONB NOT NULL,
    schema_cache JSONB,
    schema_cache_updated_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_databases_type ON databases(type);
CREATE INDEX idx_databases_active ON databases(is_active);
`

#### 5.2.5 Queries Table

`sql
CREATE TABLE queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    database_id UUID NOT NULL REFERENCES databases(id),
    natural_language TEXT NOT NULL,
    generated_sql TEXT,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN (
        'pending', 'executing', 'completed', 'failed', 'cancelled'
    )),
    result_cache_key VARCHAR(255),
    row_count INTEGER DEFAULT 0,
    execution_time_ms INTEGER,
    tokens_used INTEGER,
    conversation_id UUID,
    parent_query_id UUID REFERENCES queries(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_queries_user ON queries(user_id);
CREATE INDEX idx_queries_database ON queries(database_id);
CREATE INDEX idx_queries_status ON queries(status);
CREATE INDEX idx_queries_created ON queries(created_at DESC);
`

#### 5.2.6 Dashboards Table

`sql
CREATE TABLE dashboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    layout_config JSONB DEFAULT '{"columns": 12, "rowHeight": 50}',
    theme VARCHAR(50) DEFAULT 'default',
    is_template BOOLEAN DEFAULT FALSE,
    is_public BOOLEAN DEFAULT FALSE,
    auto_generated BOOLEAN DEFAULT FALSE,
    refresh_interval INTEGER,
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
`

#### 5.2.7 Widgets Table

`sql
CREATE TABLE widgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dashboard_id UUID NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
    query_id UUID REFERENCES queries(id),
    widget_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    position_x INTEGER DEFAULT 0,
    position_y INTEGER DEFAULT 0,
    width INTEGER DEFAULT 6,
    height INTEGER DEFAULT 4,
    config JSONB DEFAULT '{}',
    refresh_interval INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
`

#### 5.2.8 Anomalies Table

`sql
CREATE TABLE anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    database_id UUID NOT NULL REFERENCES databases(id),
    table_name VARCHAR(255) NOT NULL,
    column_name VARCHAR(255) NOT NULL,
    anomaly_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    detected_value NUMERIC,
    expected_min NUMERIC,
    expected_max NUMERIC,
    z_score NUMERIC,
    context_data JSONB,
    root_cause_analysis TEXT,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
`

#### 5.2.9 Predictions Table

`sql
CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    database_id UUID NOT NULL REFERENCES databases(id),
    table_name VARCHAR(255) NOT NULL,
    column_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    forecast_horizon INTERVAL NOT NULL,
    forecast_data JSONB NOT NULL,
    confidence_level NUMERIC DEFAULT 0.95,
    actual_values JSONB,
    accuracy_score NUMERIC,
    mae NUMERIC,
    rmse NUMERIC,
    mape NUMERIC,
    model_params JSONB,
    training_data_size INTEGER,
    trained_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
`

#### 5.2.10 Conversations Table

`sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255),
    database_id UUID REFERENCES databases(id),
    context JSONB DEFAULT '{}',
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    tool_calls JSONB,
    tool_results JSONB,
    tokens_used INTEGER,
    model_used VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
`

#### 5.2.11 CSV Imports Table

`sql
CREATE TABLE csv_imports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    row_count INTEGER,
    column_count INTEGER,
    detected_schema JSONB,
    status VARCHAR(50) DEFAULT 'uploaded',
    validation_errors JSONB,
    imported_to_table VARCHAR(255),
    database_id UUID REFERENCES databases(id),
    import_mode VARCHAR(20) DEFAULT 'append',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);
`

#### 5.2.12 Audit Logs Table

`sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    request_id VARCHAR(255),
    duration_ms INTEGER,
    status_code INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
`


---

## 6. API Endpoints Design

### 6.1 Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | /api/v1/auth/login | User login | No |
| POST | /api/v1/auth/register | User registration | No |
| POST | /api/v1/auth/refresh | Refresh JWT token | Yes |
| POST | /api/v1/auth/logout | Invalidate token | Yes |
| POST | /api/v1/auth/forgot-password | Request password reset | No |
| POST | /api/v1/auth/reset-password | Reset password | No |
| POST | /api/v1/auth/mfa/enable | Enable MFA | Yes |
| POST | /api/v1/auth/mfa/verify | Verify MFA code | Yes |
| GET | /api/v1/auth/oauth/{provider} | OAuth redirect | No |
| GET | /api/v1/auth/oauth/{provider}/callback | OAuth callback | No |

**Request/Response Examples:**

`json
// POST /api/v1/auth/login
// Request
{
    "email": "analyst@company.com",
    "password": "secure_password",
    "mfa_code": "123456"
}

// Response 200
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
        "id": "uuid-123",
        "email": "analyst@company.com",
        "full_name": "John Analyst",
        "roles": ["analyst"],
        "permissions": ["query:create", "query:execute", "dashboard:create"]
    }
}
`

### 6.2 User Management Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | /api/v1/users/me | Get current user | Any |
| PUT | /api/v1/users/me | Update profile | Any |
| PUT | /api/v1/users/me/password | Change password | Any |
| GET | /api/v1/users | List all users | Admin |
| POST | /api/v1/users | Create user | Admin |
| GET | /api/v1/users/{id} | Get user details | Admin |
| PUT | /api/v1/users/{id} | Update user | Admin |
| DELETE | /api/v1/users/{id} | Deactivate user | Admin |
| PUT | /api/v1/users/{id}/roles | Assign roles | Admin |

### 6.3 Role and Permission Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | /api/v1/roles | List all roles | Admin |
| POST | /api/v1/roles | Create role | Admin |
| GET | /api/v1/roles/{id} | Get role details | Admin |
| PUT | /api/v1/roles/{id} | Update role | Admin |
| DELETE | /api/v1/roles/{id} | Delete role | Admin |
| GET | /api/v1/roles/{id}/permissions | Get role permissions | Admin |
| PUT | /api/v1/roles/{id}/permissions | Update role permissions | Admin |
| GET | /api/v1/permissions | List all permissions | Admin |

### 6.4 Database Connection Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | /api/v1/databases | List connected databases | Viewer+ |
| POST | /api/v1/databases | Add database connection | Data Manager |
| GET | /api/v1/databases/{id} | Get database details | Viewer+ |
| PUT | /api/v1/databases/{id} | Update connection | Data Manager |
| DELETE | /api/v1/databases/{id} | Remove database | Admin |
| POST | /api/v1/databases/{id}/test | Test connection | Data Manager |
| POST | /api/v1/databases/{id}/sync | Sync schema | Data Manager |
| GET | /api/v1/databases/{id}/schema | Get schema info | Viewer+ |
| GET | /api/v1/databases/{id}/tables | List tables | Viewer+ |
| GET | /api/v1/databases/{id}/tables/{table} | Get table schema | Viewer+ |

**Request/Response Examples:**

`json
// POST /api/v1/databases
// Request
{
    "name": "Production PostgreSQL",
    "type": "postgresql",
    "host": "db.company.com",
    "port": 5432,
    "database_name": "erp_production",
    "schema_name": "public",
    "username": "readonly_user",
    "password": "encrypted_password",
    "ssl": true,
    "pool_size": 10
}

// Response 201
{
    "id": "uuid-456",
    "name": "Production PostgreSQL",
    "type": "postgresql",
    "status": "connected",
    "schema": {
        "tables": 45,
        "views": 12,
        "columns": 387
    },
    "created_at": "2026-07-11T10:00:00Z"
}
`

### 6.5 Query Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| POST | /api/v1/queries | Execute natural language query | Analyst |
| POST | /api/v1/queries/sql | Execute raw SQL | Admin |
| GET | /api/v1/queries | List query history | Analyst |
| GET | /api/v1/queries/{id} | Get query details | Analyst |
| POST | /api/v1/queries/{id}/cancel | Cancel running query | Analyst |
| POST | /api/v1/queries/{id}/follow-up | Follow-up question | Analyst |
| GET | /api/v1/queries/{id}/explain | Get query explanation | Analyst |
| POST | /api/v1/queries/{id}/optimize | Get optimization suggestions | Analyst |
| POST | /api/v1/queries/{id}/visualize | Auto-generate visualization | Analyst |

**Request/Response Examples:**

`json
// POST /api/v1/queries
// Request
{
    "database_id": "uuid-456",
    "natural_language": "Show me the top 10 customers by revenue in the last quarter",
    "conversation_id": "uuid-789",
    "options": {
        "max_rows": 100,
        "timeout_seconds": 30,
        "include_metadata": true
    }
}

// Response 200
{
    "id": "uuid-012",
    "status": "completed",
    "natural_language": "Show me the top 10 customers by revenue in the last quarter",
    "generated_sql": "SELECT c.customer_id, c.name, SUM(o.total_amount) as revenue FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE o.order_date >= '2026-04-01' AND o.order_date < '2026-07-01' GROUP BY c.customer_id, c.name ORDER BY revenue DESC LIMIT 10",
    "explanation": "This query joins the customers and orders tables to calculate total revenue per customer for Q2 2026, then returns the top 10 by revenue.",
    "results": {
        "columns": ["customer_id", "name", "revenue"],
        "rows": [
            [1001, "Acme Corp", 245000.00],
            [1002, "TechStart Inc", 198500.00]
        ],
        "row_count": 10,
        "execution_time_ms": 245
    },
    "suggested_visualizations": [
        {
            "type": "bar_chart",
            "config": {"x": "name", "y": "revenue", "sort": "desc"}
        },
        {
            "type": "pie_chart",
            "config": {"label": "name", "value": "revenue"}
        }
    ],
    "tokens_used": 1250,
    "conversation_id": "uuid-789"
}
`

### 6.6 Dashboard Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | /api/v1/dashboards | List dashboards | Viewer+ |
| POST | /api/v1/dashboards | Create dashboard | Analyst |
| GET | /api/v1/dashboards/{id} | Get dashboard | Viewer+ |
| PUT | /api/v1/dashboards/{id} | Update dashboard | Analyst |
| DELETE | /api/v1/dashboards/{id} | Delete dashboard | Analyst |
| POST | /api/v1/dashboards/auto-generate | AI auto-generate | Analyst |
| POST | /api/v1/dashboards/{id}/clone | Clone dashboard | Viewer+ |
| PUT | /api/v1/dashboards/{id}/share | Share dashboard | Analyst |
| GET | /api/v1/dashboards/templates | List templates | Viewer+ |
| POST | /api/v1/dashboards/{id}/widgets | Add widget | Analyst |
| PUT | /api/v1/dashboards/{id}/widgets/{widget_id} | Update widget | Analyst |
| DELETE | /api/v1/dashboards/{id}/widgets/{widget_id} | Remove widget | Analyst |

### 6.7 Anomaly Detection Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| POST | /api/v1/anomaly/detect | Run detection | Analyst |
| GET | /api/v1/anomaly/alerts | Get active alerts | Viewer+ |
| GET | /api/v1/anomaly/alerts/{id} | Get alert details | Viewer+ |
| PUT | /api/v1/anomaly/alerts/{id}/acknowledge | Acknowledge alert | Analyst |
| PUT | /api/v1/anomaly/alerts/{id}/resolve | Resolve alert | Analyst |
| POST | /api/v1/anomaly/configure | Configure detection | Data Manager |
| GET | /api/v1/anomaly/rules | List detection rules | Viewer+ |
| POST | /api/v1/anomaly/rules | Create detection rule | Data Manager |
| GET | /api/v1/anomaly/history | Historical anomalies | Viewer+ |
| GET | /api/v1/anomaly/stats | Anomaly statistics | Viewer+ |

### 6.8 Predictive Analytics Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| POST | /api/v1/predictions/forecast | Generate forecast | Analyst |
| GET | /api/v1/predictions | List predictions | Viewer+ |
| GET | /api/v1/predictions/{id} | Get prediction | Viewer+ |
| POST | /api/v1/predictions/{id}/train | Train model | Analyst |
| GET | /api/v1/predictions/{id}/accuracy | Get accuracy metrics | Viewer+ |
| POST | /api/v1/predictions/{id}/compare | Compare models | Analyst |
| DELETE | /api/v1/predictions/{id} | Delete prediction | Analyst |
| GET | /api/v1/predictions/models | List available models | Viewer+ |

### 6.9 CSV Import Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| POST | /api/v1/import/csv/upload | Upload CSV | Data Manager |
| POST | /api/v1/import/csv/{id}/validate | Validate data | Data Manager |
| POST | /api/v1/import/csv/{id}/import | Execute import | Data Manager |
| GET | /api/v1/import/csv/{id}/status | Import status | Data Manager |
| GET | /api/v1/import/csv/{id}/preview | Preview data | Data Manager |
| POST | /api/v1/import/csv/{id}/cancel | Cancel import | Data Manager |
| GET | /api/v1/import/history | Import history | Viewer+ |

### 6.10 Export Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| POST | /api/v1/exports/pdf | Export to PDF | Viewer+ |
| POST | /api/v1/exports/excel | Export to Excel | Viewer+ |
| POST | /api/v1/exports/png | Export to PNG | Viewer+ |
| GET | /api/v1/exports/{id} | Get export details | Viewer+ |
| GET | /api/v1/exports/{id}/download | Download file | Viewer+ |
| GET | /api/v1/exports | List exports | Viewer+ |
| DELETE | /api/v1/exports/{id} | Delete export | Viewer+ |
| POST | /api/v1/exports/schedule | Schedule export | Analyst |
| GET | /api/v1/exports/schedule | List scheduled exports | Viewer+ |

### 6.11 Integration Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | /api/v1/integrations | List integrations | Viewer+ |
| POST | /api/v1/integrations | Create integration | Admin |
| GET | /api/v1/integrations/{id} | Get integration | Viewer+ |
| PUT | /api/v1/integrations/{id} | Update integration | Admin |
| DELETE | /api/v1/integrations/{id} | Delete integration | Admin |
| POST | /api/v1/integrations/{id}/test | Test connection | Admin |
| POST | /api/v1/integrations/{id}/sync | Trigger sync | Admin |
| GET | /api/v1/integrations/{id}/logs | Sync logs | Admin |

### 6.12 Voice Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| POST | /api/v1/voice/transcribe | Transcribe audio | Analyst |
| POST | /api/v1/voice/synthesize | Text to speech | Viewer+ |
| GET | /api/v1/voice/profiles | List voice profiles | Viewer+ |
| POST | /api/v1/voice/profiles | Create voice profile | Analyst |
| WebSocket | /ws/voice | Real-time voice stream | Analyst |

### 6.13 Conversation Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | /api/v1/conversations | List conversations | Analyst |
| POST | /api/v1/conversations | Start conversation | Analyst |
| GET | /api/v1/conversations/{id} | Get conversation | Analyst |
| DELETE | /api/v1/conversations/{id} | Delete conversation | Analyst |
| GET | /api/v1/conversations/{id}/messages | Get messages | Analyst |
| POST | /api/v1/conversations/{id}/messages | Send message | Analyst |

### 6.14 WebSocket Endpoints

| Endpoint | Description | Protocol |
|----------|-------------|----------|
| ws://host/ws/query/{id} | Real-time query execution updates | WebSocket |
| ws://host/ws/voice | Voice streaming | WebSocket |
| ws://host/ws/notifications | Real-time notifications | WebSocket |
| ws://host/ws/dashboard/{id} | Live dashboard updates | WebSocket |

### 6.15 API Key Management Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | /api/v1/api-keys | List API keys | Viewer+ |
| POST | /api/v1/api-keys | Create API key | Admin |
| DELETE | /api/v1/api-keys/{id} | Revoke API key | Admin |
| PUT | /api/v1/api-keys/{id} | Update API key | Admin |


---

## 7. Agent Workflow Diagrams

### 7.1 Query Processing Workflow

`
+-------------------+
|   User Input      |
| (Natural Language)|
+-------------------+
        |
        v
+-------------------+
| Intent Detection  |
| (Qwen3 8B)       |
+-------------------+
        |
        +---> [Query Type]
        |      |
        |      +---> Simple Query ---------> [SQL Generation]
        |      |                              (Qwen3 8B)
        |      +---> Complex Query --------> [Query Decomposition]
        |      |                              (Qwen3 8B)
        |      +---> Follow-up Query ------> [Context Retrieval]
        |                                     (Conversation History)
        v
+-------------------+
| Schema Context    |
| (MCP Server)      |
+-------------------+
        |
        v
+-------------------+
| SQL Generation    |
| (Qwen3 8B)        |
| - Schema-aware    |
| - Dialect-specific|
| - Optimized       |
+-------------------+
        |
        v
+-------------------+
| SQL Validation    |
| - Syntax check    |
| - Safety check    |
| - Permission check|
+-------------------+
        |
        v
+-------------------+
| Query Execution   |
| (MCP Protocol)    |
+-------------------+
        |
        +---> [Success] ---> [Result Processing]
        |                       |
        |                       v
        |                 [Response Generation]
        |                 (Natural Language)
        |                       |
        |                       v
        |                 [Visualization Suggestion]
        |
        +---> [Error] ---> [Error Analysis]
                              |
                              v
                        [Retry/Suggestion]
`

### 7.2 Conversational Follow-up Workflow

`
+-------------------+
| Follow-up Query   |
| "What about last  |
|  month?"          |
+-------------------+
        |
        v
+-------------------+
| Context Retrieval |
| - Previous query  |
| - Conversation    |
| - Selected filters|
+-------------------+
        |
        v
+-------------------+
| Context Analysis  |
| (Qwen3 8B)       |
| - What changed?   |
| - What's implied? |
+-------------------+
        |
        v
+-------------------+
| Query Modification|
| - Update WHERE    |
| - Update SELECT   |
| - Add JOINs       |
+-------------------+
        |
        v
[Execute & Return]
`

### 7.3 Root Cause Analysis Workflow

`
+-------------------+
| Anomaly Detected  |
| (Anomaly Agent)   |
+-------------------+
        |
        v
+-------------------+
| Context Gathering |
| - Historical data |
| - Related metrics |
| - External factors|
+-------------------+
        |
        v
+-------------------+
| Correlation       |
| Analysis          |
| (Qwen3 8B)        |
+-------------------+
        |
        +---> [Statistical Correlation]
        |      - Pearson/Spearman
        |      - Cross-correlation
        |
        +---> [Temporal Correlation]
        |      - Time-lagged analysis
        |      - Event correlation
        |
        +---> [Categorical Analysis]
               - Segment breakdown
               - Factor isolation
        |
        v
+-------------------+
| Root Cause        |
| Hypothesis        |
| (Qwen3 8B)        |
+-------------------+
        |
        v
+-------------------+
| Evidence          |
| Validation        |
+-------------------+
        |
        v
+-------------------+
| Report Generation |
| - Plain language   |
| - Supporting data  |
| - Recommendations  |
+-------------------+
`

### 7.4 Auto Dashboard Generation Workflow

`
+-------------------+
| User Request      |
| "Create sales     |
|  dashboard"       |
+-------------------+
        |
        v
+-------------------+
| Requirement       |
| Analysis          |
| (Qwen3 8B)        |
| - Key metrics     |
| - Time range      |
| - Dimensions      |
+-------------------+
        |
        v
+-------------------+
| Schema Exploration|
| (MCP Server)      |
| - Relevant tables |
| - Key columns     |
| - Relationships   |
+-------------------+
        |
        v
+-------------------+
| Widget Planning   |
| (Visualization    |
|  Agent)           |
+-------------------+
        |
        +---> [KPI Cards]
        |      - Revenue
        |      - Orders
        |      - Customers
        |
        +---> [Charts]
        |      - Revenue trend (line)
        |      - Top products (bar)
        |      - Category breakdown (pie)
        |
        +---> [Tables]
               - Top customers
               - Recent orders
        |
        v
+-------------------+
| Query Generation  |
| for each widget   |
+-------------------+
        |
        v
+-------------------+
| Dashboard Assembly|
| - Layout optimize |
| - Theme apply     |
| - Filter setup    |
+-------------------+
        |
        v
+-------------------+
| Dashboard Saved   |
| & Presented       |
+-------------------+
`

### 7.5 Voice Command Workflow

`
+-------------------+
| Voice Input       |
| (Microphone)      |
+-------------------+
        |
        v
+-------------------+
| Audio Stream      |
| (WebSocket)       |
+-------------------+
        |
        v
+-------------------+
| Speech-to-Text    |
| (Whisper ASR)     |
+-------------------+
        |
        v
+-------------------+
| Intent Recognition|
| (Qwen3 8B)        |
+-------------------+
        |
        +---> [Query Intent] ----> [Query Agent]
        |                            |
        +---> [Dashboard Intent] ---> [Dashboard Agent]
        |                            |
        +---> [Navigation Intent] ---> [Frontend Router]
        |                            |
        +---> [Export Intent] -------> [Export Agent]
        |
        v
+-------------------+
| Response          |
| Generation        |
| (Qwen3 8B)        |
+-------------------+
        |
        v
+-------------------+
| Text-to-Speech    |
| (KittenTTS)       |
+-------------------+
        |
        v
+-------------------+
| Audio Output      |
| (Speaker)         |
+-------------------+
`

### 7.6 Multi-Agent Orchestration (LangGraph)

`
                        +-----------------+
                        |    START        |
                        +-----------------+
                                |
                                v
                        +-----------------+
                        |   ORCHESTRATOR  |
                        |   (Supervisor)  |
                        +-----------------+
                                |
                    +-----------+-----------+
                    |           |           |
                    v           v           v
            +-----------+ +-----------+ +-----------+
            |  QUERY    | | ANALYSIS  | |  VOICE    |
            |  AGENT    | |  AGENT    | |  AGENT    |
            +-----------+ +-----------+ +-----------+
                    |           |           |
                    v           v           v
            +-----------+ +-----------+ +-----------+
            | EXECUTE   | | DETECT    | | TRANSCRIBE|
            | QUERY     | | ANOMALY   | | /SYNTHESIZE|
            +-----------+ +-----------+ +-----------+
                    |           |           |
                    v           v           v
            +-----------+ +-----------+ +-----------+
            | VISUALIZE | | PREDICT   | | RESPOND   |
            | RESULTS   | | FUTURE    | | TO USER   |
            +-----------+ +-----------+ +-----------+
                    |           |           |
                    +-----------+-----------+
                                |
                                v
                        +-----------------+
                        |      END        |
                        +-----------------+
`


---

## 8. Implementation Phases and Milestones

### Phase 1: Foundation (Weeks 1-4)

**Objective:** Establish core infrastructure and basic functionality

#### Week 1-2: Project Setup
- [ ] Initialize monorepo structure with Turborepo
- [ ] Set up Next.js frontend with TypeScript, Tailwind, Shadcn/ui
- [ ] Set up FastAPI backend with project structure
- [ ] Configure PostgreSQL database with migrations (Alembic)
- [ ] Set up Redis for caching
- [ ] Docker Compose for local development
- [ ] CI/CD pipeline setup (GitHub Actions)
- [ ] Code linting and formatting (ESLint, Ruff, Black)

#### Week 3-4: Authentication and User Management
- [ ] JWT authentication implementation
- [ ] User registration and login
- [ ] OAuth2/OIDC integration (Azure AD, Google)
- [ ] RBAC system implementation
- [ ] Role and permission management
- [ ] Session management
- [ ] Audit logging foundation
- [ ] User profile management UI

**Milestone 1 Deliverables:**
- Working authentication system
- User management dashboard
- RBAC with 4 predefined roles
- Docker-based development environment
- CI/CD pipeline

---

### Phase 2: MCP Integration (Weeks 5-8)

**Objective:** Implement database connectivity via MCP

#### Week 5-6: MCP Server Foundation
- [ ] MCP protocol implementation in Python
- [ ] PostgreSQL MCP server
- [ ] MySQL MCP server
- [ ] SQL Server MCP server
- [ ] MongoDB MCP server
- [ ] Connection pooling and management
- [ ] Schema introspection
- [ ] Query execution pipeline

#### Week 7-8: Database Management UI
- [ ] Database connection form
- [ ] Schema browser component
- [ ] Table/column explorer
- [ ] Connection testing
- [ ] Schema caching and sync
- [ ] Database health monitoring
- [ ] Query history with database context

**Milestone 2 Deliverables:**
- 4 working MCP servers
- Database connection management
- Schema browser UI
- Connection testing functionality
- Schema sync mechanism

---

### Phase 3: AI Query Engine (Weeks 9-14)

**Objective:** Implement natural language querying with Qwen3 8B

#### Week 9-10: LLM Integration
- [ ] Qwen3 8B model loading and configuration
- [ ] vLLM serving setup for inference
- [ ] Model prompt engineering for SQL generation
- [ ] Schema-to-context conversion
- [ ] SQL dialect handling (PostgreSQL, MySQL, SQL Server)
- [ ] Query validation and safety checks

#### Week 11-12: Query Agent
- [ ] LangGraph agent setup
- [ ] Query Agent implementation
- [ ] Natural language to SQL translation
- [ ] Multi-step query decomposition
- [ ] Query optimization suggestions
- [ ] SQL explanation generation
- [ ] Error handling and retry logic

#### Week 13-14: Conversational Interface
- [ ] Conversation context management
- [ ] Follow-up query handling
- [ ] Multi-turn conversation support
- [ ] Query history and re-run
- [ ] Query templates library
- [ ] Auto-suggestions

**Milestone 3 Deliverables:**
- Working natural language to SQL translation
- Query Agent with context awareness
- Conversational follow-up support
- Query history and templates
- SQL explanation feature

---

### Phase 4: Visualization and Dashboards (Weeks 15-18)

**Objective:** Implement auto-dashboard generation and visualization

#### Week 15-16: Visualization Engine
- [ ] Chart type recommendation system
- [ ] Auto-configuration based on data characteristics
- [ ] Recharts integration with custom components
- [ ] Responsive chart layouts
- [ ] Color scheme management
- [ ] Accessibility compliance

#### Week 17-18: Dashboard System
- [ ] Dashboard CRUD operations
- [ ] Drag-and-drop widget arrangement
- [ ] Auto-dashboard generation from natural language
- [ ] Dashboard templates
- [ ] Real-time data refresh
- [ ] Dashboard sharing and permissions
- [ ] Filter management

**Milestone 4 Deliverables:**
- Auto-dashboard generation
- 14+ chart types supported
- Drag-and-drop interface
- Dashboard templates
- Real-time refresh capability

---

### Phase 5: Voice Interface (Weeks 19-21)

**Objective:** Implement voice commands and TTS output

#### Week 19: Speech-to-Text
- [ ] Whisper ASR integration
- [ ] Audio streaming via WebSocket
- [ ] Real-time transcription
- [ ] Noise cancellation
- [ ] Multi-language support

#### Week 20: Text-to-Speech
- [ ] KittenTTS integration
- [ ] Voice profile management
- [ ] Audio output streaming
- [ ] Voice speed/pitch control
- [ ] Pronunciation customization

#### Week 21: Voice Commands
- [ ] Voice command intent recognition
- [ ] Voice-to-query pipeline
- [ ] Voice dashboard navigation
- [ ] Voice export commands
- [ ] Push-to-talk and hands-free modes

**Milestone 5 Deliverables:**
- Working voice-to-text transcription
- TTS output with KittenTTS
- Voice command system
- Real-time voice streaming
- Voice profile management

---

### Phase 6: Advanced Analytics (Weeks 22-26)

**Objective:** Implement anomaly detection and predictive analytics

#### Week 22-23: Anomaly Detection
- [ ] Isolation Forest implementation
- [ ] Z-score and IQR methods
- [ ] Multi-dimensional anomaly detection
- [ ] Real-time monitoring setup
- [ ] Alert notification system
- [ ] Anomaly visualization
- [ ] Historical anomaly tracking

#### Week 24-25: Root Cause Analysis
- [ ] Statistical correlation analysis
- [ ] Temporal pattern detection
- [ ] AI-powered root cause hypothesis
- [ ] Evidence validation
- [ ] Report generation
- [ ] Correlation heatmaps

#### Week 26: Predictive Analytics
- [ ] Prophet integration
- [ ] ARIMA model
- [ ] LSTM model (optional)
- [ ] Model selection and tuning
- [ ] Accuracy tracking
- [ ] Confidence intervals
- [ ] Forecast visualization

**Milestone 6 Deliverables:**
- Real-time anomaly detection
- Root cause analysis reports
- Forecasting with 3+ models
- Model accuracy tracking
- Anomaly alerting system

---

### Phase 7: Data Import and Export (Weeks 27-28)

**Objective:** Implement CSV import and multi-format export

#### Week 27: CSV Import
- [ ] File upload handling
- [ ] Schema inference from CSV
- [ ] Data validation
- [ ] Type detection and conversion
- [ ] Duplicate handling
- [ ] Import progress tracking
- [ ] Import history

#### Week 28: Export System
- [ ] PDF report generation
- [ ] Excel export with formatting
- [ ] PNG dashboard capture
- [ ] Export templates
- [ ] Scheduled exports
- [ ] Email delivery

**Milestone 7 Deliverables:**
- CSV import with validation
- PDF/Excel/PNG export
- Export templates
- Scheduled export capability
- Import/export history

---

### Phase 8: API and Integration (Weeks 29-30)

**Objective:** Implement API for third-party integration

#### Week 29: API Key Management
- [ ] API key generation and management
- [ ] Rate limiting configuration
- [ ] API documentation (OpenAPI/Swagger)
- [ ] API usage analytics
- [ ] Webhook support

#### Week 30: Integration Framework
- [ ] REST API connector base
- [ ] OAuth2 integration connector
- [ ] Webhook receiver
- [ ] Data sync scheduling
- [ ] Integration health monitoring
- [ ] Integration marketplace (future)

**Milestone 8 Deliverables:**
- API key management system
- Rate limiting and analytics
- OpenAPI documentation
- Webhook support
- Integration framework

---

### Phase 9: Testing and Optimization (Weeks 31-34)

**Objective:** Comprehensive testing and performance optimization

#### Week 31-32: Testing
- [ ] Unit tests (90%+ coverage)
- [ ] Integration tests
- [ ] E2E tests (Playwright)
- [ ] Load testing (k6)
- [ ] Security testing (OWASP)
- [ ] Accessibility testing (WCAG 2.1)

#### Week 33-34: Optimization
- [ ] Query performance optimization
- [ ] Caching strategy implementation
- [ ] Frontend performance (Core Web Vitals)
- [ ] Database query optimization
- [ ] Model inference optimization
- [ ] Memory and CPU profiling

**Milestone 9 Deliverables:**
- 90%+ test coverage
- Performance benchmarks
- Security audit report
- Accessibility compliance report
- Optimization documentation

---

### Phase 10: Production Deployment (Weeks 35-36)

**Objective:** Production deployment and launch preparation

#### Week 35: Infrastructure
- [ ] Kubernetes cluster setup
- [ ] Helm charts for all services
- [ ] SSL/TLS configuration
- [ ] CDN setup
- [ ] Database replication
- [ ] Backup and recovery procedures

#### Week 36: Launch
- [ ] Production deployment
- [ ] Monitoring and alerting setup
- [ ] Documentation finalization
- [ ] User training materials
- [ ] Support process establishment
- [ ] Go-live checklist
- [ ] Post-launch monitoring

**Milestone 10 Deliverables:**
- Production-ready deployment
- Monitoring and alerting
- Complete documentation
- Training materials
- Support procedures

---

### Project Timeline Summary

| Phase | Weeks | Duration | Focus Area |
|-------|-------|----------|------------|
| Phase 1 | 1-4 | 4 weeks | Foundation and Auth |
| Phase 2 | 5-8 | 4 weeks | MCP Integration |
| Phase 3 | 9-14 | 6 weeks | AI Query Engine |
| Phase 4 | 15-18 | 4 weeks | Visualization |
| Phase 5 | 19-21 | 3 weeks | Voice Interface |
| Phase 6 | 22-26 | 5 weeks | Advanced Analytics |
| Phase 7 | 27-28 | 2 weeks | Import/Export |
| Phase 8 | 29-30 | 2 weeks | API Integration |
| Phase 9 | 31-34 | 4 weeks | Testing |
| Phase 10 | 35-36 | 2 weeks | Deployment |
| **Total** | **1-36** | **36 weeks** | **Full Platform** |


---

## 9. Testing Strategy

### 9.1 Testing Pyramid

`
                    +-------------------+
                    |   E2E Tests       |
                    |   (Playwright)    |
                    |   100 tests       |
                    +-------------------+
                   /                     \
                  /                       \
         +-------------------+   +-------------------+
         | Integration Tests|   | Performance Tests |
         | (pytest)         |   | (k6)              |
         | 500 tests        |   | 50 scenarios      |
         +-------------------+   +-------------------+
        /                                             \
       /                                               \
+-------------------+-------------------+-------------------+
|              Unit Tests (pytest, Jest)                    |
|                   2000+ tests                            |
+-----------------------------------------------------------+
`

### 9.2 Unit Tests

#### Backend Unit Tests

`python
# tests/unit/test_query_agent.py

import pytest
from app.agents.query_agent import QueryAgent
from app.models.database import Database

class TestQueryAgent:
    @pytest.fixture
    def agent(self):
        return QueryAgent(model="qwen3-8b")

    def test_intent_extraction(self, agent):
        result = agent.extract_intent("Show me sales by region for Q2")
        assert result.intent == "query"
        assert result.entities["time_range"] == "Q2 2026"
        assert result.entities["metric"] == "sales"
        assert result.entities["dimension"] == "region"

    def test_sql_generation(self, agent, mock_schema):
        sql = agent.generate_sql(
            "Top 10 customers by revenue",
            schema=mock_schema
        )
        assert "SELECT" in sql
        assert "customers" in sql
        assert "revenue" in sql
        assert "ORDER BY" in sql
        assert "LIMIT 10" in sql

    def test_sql_safety_check(self, agent):
        assert agent.validate_sql("SELECT * FROM users") == True
        assert agent.validate_sql("DROP TABLE users") == False
        assert agent.validate_sql("DELETE FROM users") == False
        assert agent.validate_sql("UPDATE users SET x=1") == False

    def test_follow_up_context(self, agent, conversation_history):
        result = agent.process_follow_up(
            "What about last month?",
            history=conversation_history
        )
        assert result.modified_query is not None
        assert "last_month" in result.modified_query.lower()
`

#### Frontend Unit Tests

`	ypescript
// __tests__/components/QueryInput.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import { QueryInput } from '@/components/QueryInput';

describe('QueryInput', () => {
  it('renders input field', () => {
    render(<QueryInput onSubmit={jest.fn()} />);
    expect(screen.getByPlaceholderText(/ask a question/i)).toBeInTheDocument();
  });

  it('calls onSubmit with query text', () => {
    const mockSubmit = jest.fn();
    render(<QueryInput onSubmit={mockSubmit} />);

    const input = screen.getByPlaceholderText(/ask a question/i);
    fireEvent.change(input, { target: { value: 'Show me sales data' } });
    fireEvent.keyPress(input, { key: 'Enter' });

    expect(mockSubmit).toHaveBeenCalledWith('Show me sales data');
  });

  it('shows loading state during query execution', () => {
    render(<QueryInput onSubmit={jest.fn()} isLoading={true} />);
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });
});
`

### 9.3 Integration Tests

`python
# tests/integration/test_query_flow.py

import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
class TestQueryFlow:
    async def test_complete_query_flow(self, client: AsyncClient, auth_headers):
        # Step 1: Create database connection
        db_response = await client.post(
            "/api/v1/databases",
            json={
                "name": "Test DB",
                "type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "database_name": "test_db",
                "username": "test",
                "password": "test"
            },
            headers=auth_headers
        )
        assert db_response.status_code == 201
        db_id = db_response.json()["id"]

        # Step 2: Execute natural language query
        query_response = await client.post(
            "/api/v1/queries",
            json={
                "database_id": db_id,
                "natural_language": "Show me total users by month"
            },
            headers=auth_headers
        )
        assert query_response.status_code == 200
        assert query_response.json()["status"] == "completed"
        assert "generated_sql" in query_response.json()

        # Step 3: Auto-generate visualization
        viz_response = await client.post(
            f"/api/v1/queries/{query_response.json()['id']}/visualize",
            headers=auth_headers
        )
        assert viz_response.status_code == 200
        assert "chart_type" in viz_response.json()

    async def test_conversational_follow_up(self, client, auth_headers):
        # Initial query
        response1 = await client.post(
            "/api/v1/queries",
            json={
                "database_id": "test-db-id",
                "natural_language": "Show me sales by region"
            },
            headers=auth_headers
        )
        conversation_id = response1.json()["conversation_id"]

        # Follow-up
        response2 = await client.post(
            "/api/v1/queries",
            json={
                "database_id": "test-db-id",
                "natural_language": "What about this quarter?",
                "conversation_id": conversation_id
            },
            headers=auth_headers
        )
        assert response2.status_code == 200
        assert "Q2 2026" in response2.json()["generated_sql"]
`

### 9.4 End-to-End Tests

`	ypescript
// e2e/query.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Query Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email"]', 'analyst@company.com');
    await page.fill('[data-testid="password"]', 'password');
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('/dashboard');
  });

  test('should execute natural language query', async ({ page }) => {
    // Navigate to query page
    await page.click('[data-testid="nav-query"]');

    // Enter query
    const queryInput = page.locator('[data-testid="query-input"]');
    await queryInput.fill('Show me top 10 customers by revenue');
    await queryInput.press('Enter');

    // Wait for results
    await expect(page.locator('[data-testid="query-status"]')).toHaveText('Completed');

    // Verify SQL was generated
    await expect(page.locator('[data-testid="sql-preview"]')).toBeVisible();

    // Verify results table
    const resultsTable = page.locator('[data-testid="results-table"]');
    await expect(resultsTable).toBeVisible();
    await expect(resultsTable.locator('tbody tr')).toHaveCount(10);
  });

  test('should auto-generate dashboard', async ({ page }) => {
    await page.click('[data-testid="nav-dashboards"]');
    await page.click('[data-testid="create-dashboard"]');

    // Describe dashboard
    await page.fill(
      '[data-testid="dashboard-description"]',
      'Sales performance dashboard with revenue trends and top products'
    );
    await page.click('[data-testid="auto-generate"]');

    // Wait for generation
    await expect(page.locator('[data-testid="generation-progress"]')).toBeVisible();
    await expect(page.locator('[data-testid="generation-complete"]')).toBeVisible({ timeout: 60000 });

    // Verify widgets were created
    await expect(page.locator('[data-testid="widget"]')).toHaveCount({ minimum: 3 });
  });
});
`

### 9.5 Performance Tests

`javascript
// performance/k6-query-test.js

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up
    { duration: '5m', target: 100 },   // Stay at 100 users
    { duration: '2m', target: 200 },   // Ramp to 200
    { duration: '5m', target: 200 },   // Stay at 200 users
    { duration: '2m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],  // 95% of requests under 2s
    http_req_failed: ['rate<0.01'],     // Less than 1% failures
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  // Authenticate
  const loginRes = http.post(${BASE_URL}/api/v1/auth/login, JSON.stringify({
    email: 'loadtest@company.com',
    password: 'testpassword',
  }), { headers: { 'Content-Type': 'application/json' } });

  const token = loginRes.json('access_token');
  const headers = {
    'Authorization': Bearer ,
    'Content-Type': 'application/json',
  };

  // Execute query
  const queryRes = http.post(${BASE_URL}/api/v1/queries, JSON.stringify({
    database_id: 'test-db-id',
    natural_language: 'Show me sales by region for Q2',
  }), { headers });

  check(queryRes, {
    'query status is 200': (r) => r.status === 200,
    'query completed': (r) => r.json('status') === 'completed',
    'response time < 2s': (r) => r.timings.duration < 2000,
  });

  sleep(1);
}
`

### 9.6 Security Tests

`python
# tests/security/test_auth_security.py

import pytest
from httpx import AsyncClient

class TestAuthSecurity:
    async def test_sql_injection_prevention(self, client, auth_headers):
        response = await client.post(
            "/api/v1/queries",
            json={
                "database_id": "test-db-id",
                "natural_language": "'; DROP TABLE users; --"
            },
            headers=auth_headers
        )
        # Should not execute DROP statement
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            assert "DROP" not in response.json().get("generated_sql", "")

    async def test_rbac_enforcement(self, client, viewer_headers):
        # Viewer should not be able to create queries
        response = await client.post(
            "/api/v1/queries",
            json={
                "database_id": "test-db-id",
                "natural_language": "Show me all users"
            },
            headers=viewer_headers
        )
        assert response.status_code == 403

    async def test_jwt_expiration(self, client, expired_token_headers):
        response = await client.get(
            "/api/v1/users/me",
            headers=expired_token_headers
        )
        assert response.status_code == 401

    async def test_rate_limiting(self, client, auth_headers):
        # Send 100 requests rapidly
        responses = []
        for _ in range(100):
            response = await client.get(
                "/api/v1/databases",
                headers=auth_headers
            )
            responses.append(response)

        # Some should be rate limited
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0
`

### 9.7 Test Coverage Requirements

| Module | Minimum Coverage | Target Coverage |
|--------|------------------|-----------------|
| Backend Core | 90% | 95% |
| AI Agents | 85% | 90% |
| MCP Servers | 90% | 95% |
| Frontend Components | 85% | 90% |
| Frontend Pages | 80% | 85% |
| E2E Critical Paths | 100% | 100% |
| Security | 100% | 100% |


---

## 10. Deployment Considerations

### 10.1 Infrastructure Architecture

`
+===========================================================================+
|                         PRODUCTION ENVIRONMENT                             |
+===========================================================================+
|                                                                           |
|  +-------------------------------------------------------------------+   |
|  |                        CDN (CloudFlare)                           |   |
|  +-------------------------------------------------------------------+   |
|                               |                                           |
|                               v                                           |
|  +-------------------------------------------------------------------+   |
|  |                     Load Balancer (NGINX/ALB)                      |   |
|  +-------------------------------------------------------------------+   |
|                               |                                           |
|              +----------------+----------------+                         |
|              v                v                v                         |
|  +------------------+ +------------------+ +------------------+           |
|  | Web App (Next.js)| | Web App (Next.js)| | Web App (Next.js)|           |
|  | Pod 1            | | Pod 2            | | Pod 3            |           |
|  +------------------+ +------------------+ +------------------+           |
|                               |                                           |
|                               v                                           |
|  +-------------------------------------------------------------------+   |
|  |                   API Gateway (Kong)                               |   |
|  +-------------------------------------------------------------------+   |
|                               |                                           |
|              +----------------+----------------+                         |
|              v                v                v                         |
|  +------------------+ +------------------+ +------------------+           |
|  | Backend (FastAPI)| | Backend (FastAPI)| | Backend (FastAPI)|           |
|  | Pod 1            | | Pod 2            | | Pod 3            |           |
|  +------------------+ +------------------+ +------------------+           |
|                               |                                           |
|              +----------------+----------------+                         |
|              v                v                v                         |
|  +------------------+ +------------------+ +------------------+           |
|  | MCP Server       | | MCP Server       | | MCP Server       |           |
|  | (PostgreSQL)     | | (MySQL)          | | (SQL Server)     |           |
|  +------------------+ +------------------+ +------------------+           |
|                               |                                           |
|                               v                                           |
|  +-------------------------------------------------------------------+   |
|  |                    AI Inference Cluster                            |   |
|  |  +------------------+ +------------------+ +------------------+    |   |
|  |  | vLLM (Qwen3 8B) | | vLLM (Qwen3 8B) | | Whisper Server   |    |   |
|  |  | GPU Node 1       | | GPU Node 2       | | CPU Node 1       |    |   |
|  |  +------------------+ +------------------+ +------------------+    |   |
|  |  +------------------+                                             |   |
|  |  | KittenTTS        |                                             |   |
|  |  | CPU Node 1       |                                             |   |
|  |  +------------------+                                             |   |
|  +-------------------------------------------------------------------+   |
|                               |                                           |
|              +----------------+----------------+                         |
|              v                v                v                         |
|  +------------------+ +------------------+ +------------------+           |
|  | PostgreSQL       | | Redis Cluster    | | MinIO/S3         |           |
|  | (Primary +       | | (3 nodes)        | | (Object Storage) |           |
|  |  Replica)        | |                  | |                  |           |
|  +------------------+ +------------------+ +------------------+           |
|                               |                                           |
|                               v                                           |
|  +-------------------------------------------------------------------+   |
|  |              Monitoring and Logging                                 |   |
|  |  +------------------+ +------------------+ +------------------+    |   |
|  |  | Prometheus       | | Grafana          | | ELK Stack        |    |   |
|  |  +------------------+ +------------------+ +------------------+    |   |
|  +-------------------------------------------------------------------+   |
+===========================================================================+
`

### 10.2 Kubernetes Resources

#### Resource Requests and Limits

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit | GPU |
|-----------|-------------|-----------|----------------|--------------|-----|
| Web App | 250m | 500m | 256Mi | 512Mi | - |
| Backend API | 500m | 1000m | 512Mi | 1Gi | - |
| MCP Server | 250m | 500m | 256Mi | 512Mi | - |
| vLLM (Qwen3) | 2000m | 4000m | 8Gi | 16Gi | 1x A100 |
| Whisper | 1000m | 2000m | 2Gi | 4Gi | - |
| KittenTTS | 500m | 1000m | 1Gi | 2Gi | - |
| PostgreSQL | 1000m | 2000m | 2Gi | 4Gi | - |
| Redis | 500m | 1000m | 1Gi | 2Gi | - |

#### Horizontal Pod Autoscaler

`yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
`

### 10.3 Environment Configuration

#### Development
- Docker Compose with hot reload
- Local PostgreSQL and Redis
- Mock AI services (faster iteration)
- Debug mode enabled

#### Staging
- Kubernetes with production-like config
- Shared PostgreSQL (separate schema)
- Real AI services (smaller models optional)
- Performance testing enabled

#### Production
- Full Kubernetes cluster
- HA PostgreSQL with replication
- Redis Cluster
- GPU nodes for AI inference
- Full monitoring and alerting

### 10.4 Monitoring and Alerting

#### Prometheus Metrics

`python
# app/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Query metrics
query_total = Counter('analytics_queries_total', 'Total queries executed', ['status', 'database_type'])
query_duration = Histogram('analytics_query_duration_seconds', 'Query execution duration', ['database_type'])
query_rows = Histogram('analytics_query_rows', 'Query result rows', ['database_type'])

# AI metrics
llm_inference_duration = Histogram('llm_inference_duration_seconds', 'LLM inference duration', ['model'])
llm_tokens_used = Counter('llm_tokens_total', 'Total LLM tokens used', ['model'])
llm_errors = Counter('llm_errors_total', 'LLM inference errors', ['model'])

# System metrics
active_users = Gauge('analytics_active_users', 'Currently active users')
websocket_connections = Gauge('analytics_websocket_connections', 'Active WebSocket connections')
`

### 10.5 Security Considerations

#### Network Security
- All external traffic via HTTPS (TLS 1.3)
- Internal service mesh (Istio/Linkerd)
- Network policies for pod-to-pod communication
- WAF (Web Application Firewall) at edge

#### Data Security
- Encryption at rest (AES-256) for database
- Encryption in transit (TLS) for all connections
- Secrets management (HashiCorp Vault)
- PII data masking in logs

#### Application Security
- OWASP Top 10 compliance
- SQL injection prevention (parameterized queries)
- XSS protection (Content Security Policy)
- CSRF protection (SameSite cookies)
- Rate limiting per user/IP
- Input validation and sanitization

#### Compliance
- GDPR compliance (data export, deletion)
- SOC 2 Type II readiness
- Audit logging for all operations
- Data retention policies

### 10.6 Disaster Recovery

#### Backup Strategy
- **PostgreSQL**: Daily full backups + WAL archiving (point-in-time recovery)
- **Redis**: RDB snapshots every 6 hours + AOF
- **Object Storage**: Versioning enabled, cross-region replication
- **Configuration**: Git-based, immutable

#### Recovery Procedures
- **RTO (Recovery Time Objective)**: 4 hours
- **RPO (Recovery Point Objective)**: 1 hour

#### Failover Plan
1. Database: Automatic failover to replica
2. Application: Kubernetes self-healing (restart pods)
3. AI Services: Fallback to CPU inference
4. Full region failover: Manual trigger with DNS switch


---

## 11. Risk Assessment and Mitigation

### 11.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM generates incorrect SQL | High | High | SQL validation, sandboxed execution, human review option |
| Model inference latency | Medium | High | vLLM optimization, caching, async processing |
| MCP server instability | Medium | High | Circuit breaker pattern, fallback queries, health monitoring |
| Database schema changes | High | Medium | Schema sync, graceful degradation, versioned schemas |
| Voice recognition accuracy | Medium | Medium | Multi-model fallback, confidence thresholds, text input backup |
| Scale beyond capacity | Low | High | Auto-scaling, load testing, performance budgets |

### 11.2 Business Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| User adoption resistance | Medium | High | Training programs, intuitive UI, gradual rollout |
| Data privacy concerns | Medium | High | RBAC, data masking, audit logs, compliance certifications |
| Integration complexity | High | Medium | Phased rollout, dedicated integration team, extensive testing |
| Cost overrun | Medium | High | Fixed-price phases, regular reviews, contingency budget |

### 11.3 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Key personnel departure | Low | High | Documentation, cross-training, knowledge base |
| Security breach | Low | Critical | Security audits, penetration testing, incident response plan |
| Vendor lock-in | Medium | Medium | Open standards (MCP), abstraction layers, multi-vendor strategy |

---

## 12. Appendices

### Appendix A: MCP Protocol Specification

The Model Context Protocol (MCP) provides a standardized way for AI models to interact with external data sources and tools. Key concepts:

1. **MCP Server**: Exposes tools and resources that AI models can discover and use
2. **MCP Client**: Connects to MCP servers to access their capabilities
3. **Tools**: Functions that can be called by the AI model
4. **Resources**: Data that can be read by the AI model
5. **Prompts**: Pre-defined templates for common interactions

### Appendix B: Qwen3 8B Prompt Templates

**SQL Generation Prompt:**
- Database schema context injection
- User question parsing
- SQL dialect-specific generation
- Result limit and safety constraints

**Follow-up Query Prompt:**
- Previous query context
- Conversation history
- Query modification instructions

**Root Cause Analysis Prompt:**
- Anomaly context and metrics
- Statistical analysis instructions
- Hypothesis generation framework

### Appendix C: KittenTTS Configuration

- Model: kittentts-1 (Apache 2.0 license)
- Device: CPU-only inference
- Sample rate: 22050 Hz
- Voice profiles: default, professional, friendly

### Appendix D: Environment Variables

Backend: DATABASE_URL, REDIS_URL, SECRET_KEY
AI Models: VLLM_HOST, VLLM_PORT, QWEN3_MODEL_PATH
MCP Servers: MCP_POSTGRESQL_URL, MCP_MYSQL_URL, MCP_SQLSERVER_URL
Storage: S3_BUCKET, S3_ENDPOINT
Monitoring: PROMETHEUS_PORT, GRAFANA_PORT

### Appendix E: Export Templates

PDF Report: Header/footer layout, chart styling, table formatting
Excel Export: Multiple sheets, auto-filter, conditional formatting
PNG Export: Dashboard screenshot, chart capture, branding options

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | July 11, 2026 | Platform Team | Initial comprehensive project plan |

---

**End of Document**


