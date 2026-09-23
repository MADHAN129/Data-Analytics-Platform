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
