# Project Creation Prompt

This document contains the master prompt that was used to create the PostgreSQL to Snowflake Migration Agent. Use this prompt to understand the project genesis or to recreate a similar migration tool.

---

## Master Prompt

```
Create a production-grade PostgreSQL to Snowflake database migration agent with the following specifications:

## PROJECT OVERVIEW
Build a comprehensive, web-based database migration tool that analyzes PostgreSQL databases, generates optimized Snowflake schemas, and executes end-to-end migrations with full auditability and validation.

## CORE REQUIREMENTS

### 1. Technology Stack
**Backend:**
- Python 3.11+ with FastAPI for REST API
- Pydantic for data validation and schemas
- psycopg2 for PostgreSQL connectivity
- snowflake-connector-python for Snowflake
- Structured logging with NDJSON format
- Async/await for performance

**Frontend:**
- React 18 with TypeScript
- TailwindCSS for styling
- Vite for build tooling
- Axios for API communication
- Real-time progress polling

**Infrastructure:**
- Docker and Docker Compose support
- VS Code Dev Container configuration
- MCP (Model Context Protocol) server for AI assistant integration

### 2. Authentication & Security
- Okta External OAuth for Snowflake authentication
- No password storage - OAuth token-based
- Credential redaction in logs
- Secure environment variable management
- SSL/TLS support for database connections

### 3. Core Features

#### Phase 1: Analysis
**PostgreSQL Introspection:**
- Query information_schema and pg_catalog
- Extract all tables, columns, constraints, indexes
- Capture primary keys, foreign keys, unique constraints
- Identify data types (including JSON, arrays, enums, UUID, BYTEA)
- Calculate volumetrics (row counts, sizes)
- Detect compatibility issues

**Output:**
- Complete analysis report in JSON
- Volumetrics summary
- Compatibility assessment
- Special type identification

#### Phase 2: Schema Generation
**Type Mapping System:**
- INTEGER → NUMBER(10,0)
- BIGINT → NUMBER(19,0)
- VARCHAR(n) → VARCHAR(n)
- TEXT → VARCHAR
- JSONB/JSON → VARIANT
- BYTEA → BINARY
- UUID → VARCHAR(36)
- ARRAY[] → VARIANT
- ENUM → VARCHAR
- TIMESTAMP → TIMESTAMP_NTZ
- TIMESTAMPTZ → TIMESTAMP_TZ
- SERIAL → IDENTITY or SEQUENCE

**DDL Generation:**
- CREATE TABLE statements with all columns
- NOT NULL constraints
- Primary keys (as metadata - not enforced)
- Unique constraints (as metadata)
- Comments and documentation
- Identity/sequence handling
- Case style transformation (UPPER/LOWER/PRESERVE)

**Output:**
- Complete Snowflake DDL script
- Type mapping decisions with rationale (YAML)
- Improvement recommendations (Markdown)
- Cluster key suggestions

#### Phase 3: Data Migration
**Extract from PostgreSQL:**
- Server-side cursors for memory efficiency
- Chunking (configurable size, default 200MB)
- Support for CSV and Parquet formats
- GZIP compression
- NULL handling
- Special character escaping
- Progress tracking per table

**Load to Snowflake:**
- Upload files to named stage using PUT
- COPY INTO commands with MATCH_BY_COLUMN_NAME
- Parallel table loading (configurable workers)
- Retry logic with exponential backoff
- Error handling and recovery
- Idempotent operations

**Parallelism:**
- ThreadPoolExecutor for concurrent table migrations
- Configurable worker count (1-16)
- Independent database connections per worker
- Progress aggregation

#### Phase 4: Validation
**Post-Migration Checks:**
- Row count comparison (source vs target)
- NOT NULL constraint verification
- Primary key duplicate detection
- JSON validity checks (TRY_PARSE_JSON)
- Timestamp sanity checks
- Data sampling and comparison

**Output:**
- Validation results JSON
- Post-migration SQL checks script
- Summary report with pass/fail status

#### Phase 5: Reporting
**Artifacts Generated:**
- analysis_report.json
- snowflake_objects.sql
- mapping_decisions.yml
- improvement_recommendations.md
- post_migration_checks.sql
- validation_results.json
- summary.md
- run_log.ndjson (structured logs)

### 4. Web Interface Features
**Configuration Form:**
- PostgreSQL connection details (host, port, database, credentials, schemas)
- SSL configuration options
- Snowflake connection details (account, warehouse, database, role, stage, file format)
- OAuth token input
- Migration preferences (format, chunk size, parallelism, case style)
- Dry run toggle
- Test connections button

**Progress Display:**
- Real-time progress percentage
- Current phase indicator
- Per-table status (pending, in progress, completed, failed)
- Row counts and duration per table
- Error messages and warnings
- Estimated time remaining

**Artifacts Viewer:**
- List all generated files
- Download individual files
- Download all as ZIP
- Preview text files in browser

### 5. API Endpoints
- POST /api/v1/migrate - Start migration
- GET /api/v1/migrate/{run_id}/progress - Get real-time progress
- GET /api/v1/migrate/{run_id}/status - Get detailed status
- GET /api/v1/migrate/{run_id}/artifacts - List artifacts
- GET /api/v1/migrate/{run_id}/artifacts/{filename} - Download artifact
- GET /api/v1/migrate/{run_id}/logs - Get structured logs
- POST /api/v1/migrate/{run_id}/cancel - Cancel migration
- DELETE /api/v1/migrate/{run_id} - Delete migration
- GET /api/v1/migrations - List all migrations
- POST /api/v1/test-connections - Test database connectivity
- GET /health - Health check

### 6. Configuration & Deployment

**Environment Configuration:**
- .env file for settings
- Configurable API host, port, log level
- CORS origins configuration
- Artifacts and temp file paths
- Secret key for security

**Docker Support:**
- Production Dockerfile with multi-stage build
- Development docker-compose.yml
- Production docker-compose.yml
- Nginx configuration for frontend
- PostgreSQL test database included

**Dev Container:**
- VS Code devcontainer.json
- Automatic setup with post-create script
- Python 3.11 and Node.js 18
- PostgreSQL client tools
- Pre-configured VS Code extensions
- Port forwarding (8000, 5173, 5432)

**MCP Server:**
- Model Context Protocol implementation
- Tools for database analysis and migration
- Resources (documentation, templates)
- Prompts for common workflows
- Integration with AI assistants like Claude

### 7. Documentation Requirements

Create comprehensive documentation:

**README.md:**
- Project overview with badges
- Key features list
- Quick start guide
- Architecture diagram
- Installation options (local, Docker, dev container)
- Usage examples
- Documentation links

**GETTING_STARTED.md:**
- Step-by-step setup from prerequisites to first migration
- Prerequisites checklist
- Installation instructions
- Okta OAuth configuration walkthrough
- Snowflake setup with SQL scripts
- PostgreSQL configuration
- Application startup
- First migration walkthrough (dry run and full)
- Results interpretation
- Troubleshooting common issues
- Quick reference card

**USER_GUIDE.md:**
- Detailed usage instructions
- Configuration options explained
- Workflow examples
- Best practices
- Dry run vs full migration
- Artifact descriptions
- Validation interpretation

**DEVELOPER_GUIDE.md:**
- Complete code walkthrough
- Module descriptions (main.py, models.py, analyzer, generator, pipeline, etc.)
- Development setup
- Testing approach
- Extension points
- Code examples
- Best practices

**INTRANET_DEPLOYMENT.md:**
- Company intranet deployment guide
- Three architecture options (single server, load balanced, Kubernetes)
- Complete security hardening (network, application, data)
- Nginx SSL configuration with security headers
- Systemd service for auto-start
- Network configuration and firewall rules
- Monitoring with Prometheus and health checks
- Log management and backup procedures
- LDAP/AD authentication integration
- Load balancer configuration
- Maintenance checklists (weekly, monthly, quarterly)
- Troubleshooting guide

**MCP_DEPLOYMENT.md:**
- Model Context Protocol extension deployment
- Integration with AI assistants (Claude Desktop, etc.)
- Configuration for macOS, Windows, and Linux
- Server deployment options (systemd, Docker, Kubernetes)
- MCP tools documentation (4 tools exposed)
- MCP resources and prompts
- Testing procedures (CLI, Python client, AI assistant)
- Authentication and authorization
- Custom tool addition examples
- Production deployment checklist
- Troubleshooting MCP issues

**SETUP.md:**
- Advanced installation options
- Okta External OAuth setup
- Snowflake security integration
- PostgreSQL permissions
- Network requirements
- SSL/TLS configuration
- Production deployment
- Environment variables

**DEVCONTAINER_GUIDE.md:**
- Dev container setup and usage
- MCP server configuration
- Docker Compose usage
- Troubleshooting dev container issues
- Examples and workflows

**ARCHITECTURE.md:**
- System architecture diagram
- Component descriptions
- Data flow diagrams
- Type mapping system
- Pipeline architecture
- Security architecture
- Performance considerations
- Monitoring and observability

**REQUIREMENTS.md:**
- System requirements (hardware, software)
- Network requirements
- Database permissions
- Third-party services
- Scalability considerations

**PROJECT_CREATION_PROMPT.md:**
- This file - the master prompt
- Step-by-step development process
- Iterative development approach
- Key decisions and rationale

### 8. Code Quality Requirements

**Python Code:**
- Type hints for all functions
- Docstrings for classes and methods
- Pydantic models for validation
- Structured logging with context
- Error handling with specific exceptions
- Resource cleanup (connections, files)
- Async/await where appropriate

**TypeScript/React Code:**
- Functional components with hooks
- TypeScript interfaces for all props
- Proper error boundaries
- Loading states
- Responsive design
- Accessibility considerations

**Testing:**
- Unit tests for core logic
- Integration tests for database operations
- API endpoint tests
- Mock external dependencies

**Code Organization:**
```
postgress-to-snowflake-migration-agent/
├── .devcontainer/          # Dev container config
├── backend/                # Python backend
│   ├── main.py            # FastAPI app
│   ├── config.py          # Configuration
│   ├── models.py          # Pydantic models
│   ├── logger.py          # Logging setup
│   ├── postgres_analyzer.py
│   ├── snowflake_generator.py
│   ├── data_pipeline.py
│   ├── validation.py
│   ├── migrator.py        # Orchestrator
│   └── mcp_server.py      # MCP implementation
├── frontend/              # React frontend
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   └── index.css
│   └── package.json
├── artifacts/             # Generated files
├── temp/                  # Temporary files
├── logs/                  # Application logs
├── .env.example           # Environment template
├── .gitignore
├── Dockerfile             # Production image
├── docker-compose.yml     # Production compose
├── docker-compose.dev.yml # Development compose
├── nginx.conf             # Nginx config
├── mcp-server.json        # MCP configuration
├── requirements.txt       # Python dependencies
├── README.md
├── GETTING_STARTED.md
├── USER_GUIDE.md
├── DEVELOPER_GUIDE.md
├── SETUP.md
├── DEVCONTAINER_GUIDE.md
├── ARCHITECTURE.md
├── REQUIREMENTS.md
└── PROJECT_CREATION_PROMPT.md
```

### 9. Error Handling & Resilience

**Retry Logic:**
- Exponential backoff for transient errors
- Configurable retry attempts
- Circuit breaker pattern for repeated failures

**Graceful Degradation:**
- Continue migration even if individual tables fail
- Collect all errors for final report
- Allow retry of failed tables

**Idempotency:**
- Safe to re-run migrations
- IF NOT EXISTS in DDL
- Track loaded files to avoid duplicates

**Logging:**
- Structured JSON logs (NDJSON)
- Request ID tracking
- Timestamp all events
- Log levels (DEBUG, INFO, WARN, ERROR)
- Credential redaction

### 10. Performance Optimizations

**Backend:**
- Async operations where possible
- Connection pooling
- Streaming for large datasets
- Server-side cursors
- Chunked processing
- Parallel table migrations

**Frontend:**
- Code splitting
- Lazy loading
- Efficient state updates
- Debounced API calls
- Memoization

**Database:**
- Batch operations
- Compression (GZIP for CSV, Snappy for Parquet)
- Efficient queries with indexes
- Minimal round trips

## IMPLEMENTATION APPROACH

### Phase 1: Core Backend (Weeks 1-2)
1. Set up FastAPI project structure
2. Implement PostgreSQL analyzer
3. Create Pydantic models
4. Build type mapping system
5. Generate Snowflake DDL

### Phase 2: Data Pipeline (Weeks 3-4)
1. Implement data extraction
2. Add file upload to Snowflake stage
3. Implement COPY INTO loading
4. Add parallelism
5. Implement validation

### Phase 3: Web Interface (Weeks 5-6)
1. Set up React project
2. Create configuration form
3. Build progress display
4. Add artifacts viewer
5. Implement API integration

### Phase 4: Integration & Testing (Week 7)
1. End-to-end testing
2. Error handling
3. Logging improvements
4. Performance tuning

### Phase 5: Containerization (Week 8)
1. Create Docker images
2. Docker Compose configs
3. Dev container setup
4. MCP server implementation

### Phase 6: Documentation (Week 9)
1. Write all documentation files
2. Create examples and tutorials
3. Add troubleshooting guides
4. Quick reference materials

### Phase 7: Polish & Release (Week 10)
1. Code review and refactoring
2. Security audit
3. Performance optimization
4. Final testing
5. Release preparation

## SUCCESS CRITERIA

The project is complete when:
- ✅ Can analyze PostgreSQL databases of any size
- ✅ Generates correct Snowflake DDL for all data types
- ✅ Successfully migrates data with validation
- ✅ Web UI is intuitive and responsive
- ✅ Dry run mode works perfectly
- ✅ Real-time progress tracking
- ✅ Comprehensive error handling
- ✅ Complete documentation (11 guides)
- ✅ Docker and dev container support
- ✅ MCP server functional with AI assistants
- ✅ Intranet deployment ready (single server, load balanced, K8s)
- ✅ Production-ready code quality with security hardening
- ✅ Monitoring and alerting configured
- ✅ Backup and disaster recovery procedures

## KEY DECISIONS & RATIONALE

1. **FastAPI over Flask:** Better async support, automatic API docs, Pydantic integration
2. **React over Vue/Angular:** Larger ecosystem, better TypeScript support
3. **TailwindCSS:** Utility-first, rapid development, consistent design
4. **OAuth over Username/Password:** More secure, no credential storage
5. **CSV and Parquet:** Wide compatibility, efficient for large datasets
6. **Chunking:** Prevents memory issues with large tables
7. **Dry Run First:** Safety - always analyze before executing
8. **Structured Logging:** Better observability, easier debugging
9. **Dev Container:** Consistent development environment across team

## NON-GOALS

What this tool does NOT do:
- ❌ Migrate views, stored procedures, functions (only tables and data)
- ❌ Continuous replication (one-time migration only)
- ❌ Automatic schema evolution
- ❌ Cross-database joins during migration
- ❌ Real-time streaming

## DEPLOYMENT OPTIONS

The migration agent supports multiple deployment scenarios:

1. **Local Development:**
   - Direct Python and Node.js execution
   - For development and testing
   - Quick iteration and debugging

2. **Docker Compose:**
   - Single-command deployment
   - Development and production modes
   - Isolated environments

3. **Dev Container:**
   - VS Code integration
   - Consistent development environment
   - Pre-configured tools and extensions

4. **Company Intranet:**
   - Single server deployment (simplest)
   - Load balanced deployment (high availability)
   - Kubernetes deployment (enterprise scale)
   - Complete security hardening
   - LDAP/AD authentication
   - Monitoring and alerting

5. **MCP Extension:**
   - AI assistant integration
   - Claude Desktop configuration
   - Natural language interface
   - Automated workflows

## FUTURE ENHANCEMENTS (Post-MVP)

Potential additions:
- View migration support
- Incremental migration support
- Migration scheduling
- Cost estimation (MCP tool available)
- Multi-region support
- Terraform/IaC generation
- Monitoring dashboard (Prometheus integration available)
- Email notifications (configured in intranet deployment)
- Slack integration (configured in intranet deployment)
- Migration templates
- Bulk migrations
- Additional AI assistant integrations (beyond Claude)
```

---

## Outcome

The above prompt results in a complete, production-ready database migration agent with:

**13 Python modules** implementing core functionality
**3 React components** for the web interface
**8 configuration files** for Docker, dev containers, and MCP
**11 documentation files** totaling ~12,000 lines
**1,363 lines** of configuration and setup code

**Total codebase:** ~18,000+ lines across backend, frontend, config, and documentation

**Documentation Suite:**
1. README.md - Project overview and quick start
2. GETTING_STARTED.md - Complete setup walkthrough (549 lines)
3. USER_GUIDE.md - Detailed usage instructions
4. DEVELOPER_GUIDE.md - Code walkthrough (773 lines)
5. SETUP.md - Advanced configuration
6. ARCHITECTURE.md - System design and components
7. REQUIREMENTS.md - System and application requirements
8. DEVCONTAINER_GUIDE.md - Dev container and MCP setup (529 lines)
9. INTRANET_DEPLOYMENT.md - Enterprise deployment guide (986 lines)
10. MCP_DEPLOYMENT.md - AI assistant integration (978 lines)
11. PROJECT_CREATION_PROMPT.md - Master prompt (687 lines)

**Deployment Options:**
- Local development (Python + Node.js)
- Docker Compose (development and production)
- VS Code Dev Container
- Company intranet (single server, load balanced, Kubernetes)
- MCP extension (Claude Desktop, AI assistants)

---

## Development Process

### Iterative Development Approach

The project was built iteratively with these steps:

1. **Initial Setup**
   - Repository structure
   - Basic FastAPI app
   - React skeleton
   - Environment configuration

2. **PostgreSQL Analyzer**
   - Connection handling
   - Schema introspection
   - Column metadata extraction
   - Constraint handling
   - Volumetrics calculation

3. **Type Mapper**
   - Type mapping rules
   - Special type handling
   - Rationale generation

4. **DDL Generator**
   - Table creation
   - Constraint metadata
   - Identity/sequence handling
   - Comments and documentation

5. **Data Pipeline**
   - CSV extraction
   - Parquet extraction
   - Snowflake stage upload
   - COPY INTO execution
   - Parallelism

6. **Validation Engine**
   - Row count verification
   - Constraint checks
   - Data quality validation

7. **Web Interface**
   - Configuration form
   - Progress display
   - Artifacts viewer
   - API integration

8. **Containerization**
   - Docker images
   - Docker Compose
   - Dev container
   - MCP server

9. **Documentation**
   - All markdown files
   - Examples and guides
   - Troubleshooting

10. **Polish**
    - Error handling
    - Logging
    - Testing
    - Performance

11. **Deployment Guides**
    - Intranet deployment documentation
    - MCP extension setup
    - Production deployment procedures
    - Monitoring and maintenance guides

---

## Key Code Patterns

### Pydantic Models for Validation
```python
class PostgresConfig(BaseModel):
    host: str
    port: int = 5432
    database: str
    username: str
    password: str
    schemas: List[str] = ["*"]
```

### Structured Logging
```python
logger.info(
    "table_migration_started",
    run_id=run_id,
    schema=schema,
    table=table,
    estimated_rows=rows
)
```

### Type Mapping Pattern
```python
def map_type(pg_type: str, **kwargs) -> Tuple[str, str]:
    # Returns (snowflake_type, rationale)
    if pg_type == "integer":
        return "NUMBER(10,0)", "Standard integer mapping"
```

### Async Background Tasks
```python
@app.post("/api/v1/migrate")
async def start_migration(
    request: MigrationRequest,
    background_tasks: BackgroundTasks
):
    run_id = str(uuid.uuid4())
    background_tasks.add_task(execute_migration, run_id, request)
    return {"run_id": run_id}
```

### React Progress Polling
```typescript
useEffect(() => {
    const interval = setInterval(async () => {
        const response = await axios.get(`/api/v1/migrate/${runId}/progress`);
        setProgress(response.data);
    }, 2000);
    return () => clearInterval(interval);
}, [runId]);
```

---

## Usage

This prompt can be used to:

1. **Understand the Project:** See the complete requirements and design decisions
2. **Train AI Models:** Use as training data for code generation
3. **Create Similar Tools:** Adapt for other database migration scenarios
4. **Onboard Team Members:** Quick overview of project goals and architecture
5. **Generate Documentation:** Auto-generate project summaries
6. **Code Reviews:** Verify implementation matches requirements

---

## Modifications for Other Use Cases

To adapt this for other migrations:

**Oracle to Snowflake:**
- Replace `postgres_analyzer.py` with `oracle_analyzer.py`
- Update type mappings for Oracle types (CLOB, BLOB, RAW, etc.)
- Modify DDL generation for Oracle-specific features

**MySQL to BigQuery:**
- Change target generator to BigQuery syntax
- Update type mappings
- Modify data loading (use BigQuery LOAD instead of COPY INTO)

**SQL Server to Redshift:**
- SQL Server introspection queries
- Redshift DDL generation
- S3-based data loading

---

**Repository:** https://github.com/Maheshgx/postgress-to-snowflake-migration-agent

**Created:** November 2024

**License:** MIT
