# Architecture Documentation

## System Overview

The PostgreSQL to Snowflake Migration Agent is a web-based application that performs auditable, end-to-end database migrations with Okta SSO integration.

```
┌──────────────────────────────────────────────────────────────────┐
│                     Migration Agent System                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────┐         ┌─────────────┐        ┌─────────────┐ │
│  │   React     │◄───────►│   FastAPI   │◄──────►│  PostgreSQL │ │
│  │  Frontend   │  HTTP   │   Backend   │  SQL   │   Database  │ │
│  │   (UI)      │         │  (Orchestr) │        │  (Source)   │ │
│  └─────────────┘         └─────────────┘        └─────────────┘ │
│        │                        │                                 │
│        │                        │                                 │
│        │                        ▼                                 │
│        │                 ┌─────────────┐                         │
│        │                 │  Snowflake  │                         │
│        └────────────────►│  Database   │                         │
│          (OAuth Token)   │  (Target)   │                         │
│                          └─────────────┘                         │
│                                 ▲                                 │
│                                 │                                 │
│                          ┌──────┴──────┐                         │
│                          │    Okta     │                         │
│                          │  OAuth SSO  │                         │
│                          └─────────────┘                         │
└──────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Frontend Layer (React + TypeScript)

**Technology Stack:**
- React 18.2
- TypeScript 5.2
- TailwindCSS 3.3
- React Query (TanStack Query)
- Axios for HTTP
- React Hook Form
- Lucide Icons

**Key Components:**

```
frontend/
├── src/
│   ├── App.tsx                    # Main application component
│   ├── main.tsx                   # Application entry point
│   ├── components/
│   │   ├── ConfigurationForm.tsx  # Migration configuration UI
│   │   ├── MigrationProgress.tsx  # Real-time progress display
│   │   └── ArtifactsViewer.tsx    # Artifacts download interface
│   ├── index.css                  # Global styles (Tailwind)
│   └── ...
```

**State Management:**
- React Query for server state
- React hooks (useState, useEffect) for local state
- No global state management needed (simple app)

**API Communication:**
- Axios HTTP client
- Auto-retry logic with exponential backoff
- Real-time polling (2-second intervals) for progress

### 2. Backend Layer (FastAPI + Python)

**Technology Stack:**
- FastAPI 0.104
- Python 3.11+
- Pydantic for data validation
- psycopg2 for PostgreSQL
- snowflake-connector-python
- Pandas/PyArrow for data processing
- Structlog for structured logging

**Module Structure:**

```
backend/
├── main.py                # FastAPI application & endpoints
├── config.py             # Configuration management
├── models.py             # Pydantic models/schemas
├── logger.py             # Structured logging setup
├── postgres_analyzer.py  # PostgreSQL introspection
├── snowflake_generator.py # DDL generation & type mapping
├── data_pipeline.py      # Extract-load pipeline
├── validation.py         # Post-migration validation
└── migrator.py           # Migration orchestration
```

**API Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Health check |
| GET | `/health` | Detailed health status |
| POST | `/api/v1/migrate` | Start migration |
| GET | `/api/v1/migrate/{run_id}/progress` | Get progress |
| GET | `/api/v1/migrate/{run_id}/status` | Get detailed status |
| GET | `/api/v1/migrate/{run_id}/artifacts` | List artifacts |
| GET | `/api/v1/migrate/{run_id}/artifacts/{filename}` | Download artifact |
| GET | `/api/v1/migrate/{run_id}/logs` | Get log entries |
| POST | `/api/v1/migrate/{run_id}/cancel` | Cancel migration |
| DELETE | `/api/v1/migrate/{run_id}` | Delete migration |
| GET | `/api/v1/migrations` | List all migrations |
| POST | `/api/v1/test-connections` | Test connectivity |

### 3. Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Migration Flow                            │
└─────────────────────────────────────────────────────────────────┘

Phase 1: ANALYZE
┌──────────────┐
│ PostgreSQL   │
│ Analyzer     │───► Query pg_catalog, information_schema
│              │───► Gather tables, columns, constraints
│              │───► Calculate volumetrics
└──────┬───────┘
       │
       ▼
   analysis_report.json


Phase 2: PLAN
┌──────────────┐
│ Snowflake    │
│ Generator    │───► Map types (PG → SF)
│              │───► Generate DDL
│              │───► Create load plan
└──────┬───────┘
       │
       ▼
   snowflake_objects.sql
   mapping_decisions.yml
   improvement_recommendations.md


Phase 3: EXECUTE (if confirmed)
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Extract    │────►│   Upload     │────►│     Load     │
│ (PostgreSQL) │     │  (Stage)     │     │ (Snowflake)  │
└──────────────┘     └──────────────┘     └──────────────┘
       │                     │                     │
       ▼                     ▼                     ▼
   CSV/Parquet          COPY Files          COPY INTO


Phase 4: VALIDATE
┌──────────────┐
│  Validator   │───► Compare row counts
│              │───► Check constraints
│              │───► Validate data quality
└──────┬───────┘
       │
       ▼
   validation_results.json


Phase 5: REPORT
┌──────────────┐
│   Reporter   │───► Generate summary
│              │───► Create checklist
└──────┬───────┘
       │
       ▼
   summary.md
   run_log.ndjson
```

## Database Introspection

### PostgreSQL Analysis Process

1. **Connect** to PostgreSQL using provided credentials
2. **Query System Catalogs:**
   - `information_schema.schemata` - Schema list
   - `information_schema.tables` - Table metadata
   - `information_schema.columns` - Column definitions
   - `information_schema.table_constraints` - PK/UK/FK/CHECK
   - `information_schema.key_column_usage` - Constraint columns
   - `information_schema.referential_constraints` - FK details
   - `pg_catalog.pg_indexes` - Index information
   - `pg_catalog.pg_class` - Table sizes, row counts
   - `pg_catalog.pg_sequences` - Sequence definitions
   - `pg_matviews` - Materialized views

3. **Analyze Special Types:**
   - JSON/JSONB columns
   - Array columns
   - Enum types
   - BYTEA (binary data)
   - UUID columns

4. **Calculate Volumetrics:**
   - Total database size
   - Per-table row counts (approximate)
   - Per-table size in bytes
   - Identify largest tables

5. **Compatibility Assessment:**
   - Reserved identifier detection
   - Wide table detection (>500 columns)
   - Large VARCHAR detection
   - LOB column identification

## Type Mapping System

### Mapping Rules

The `TypeMapper` class applies these rules:

```python
# Numeric Types
PostgreSQL          →  Snowflake
─────────────────────────────────
SMALLINT            →  NUMBER(5,0)
INTEGER             →  NUMBER(10,0)
BIGINT              →  NUMBER(19,0)
NUMERIC(p,s)        →  NUMBER(p,s)
DECIMAL(p,s)        →  NUMBER(p,s)
REAL                →  FLOAT
DOUBLE PRECISION    →  FLOAT

# String Types
VARCHAR(n)          →  VARCHAR(n)
TEXT                →  VARCHAR (unlimited)
CHAR(n)             →  CHAR(n)

# Date/Time Types
TIMESTAMP           →  TIMESTAMP_NTZ
TIMESTAMPTZ         →  TIMESTAMP_TZ
DATE                →  DATE
TIME                →  TIME

# Special Types
JSON/JSONB          →  VARIANT
BYTEA               →  BINARY
UUID                →  VARCHAR(36)
ARRAY[]             →  VARIANT
ENUM                →  VARCHAR

# Serial/Identity
SERIAL              →  NUMBER + SEQUENCE or IDENTITY
BIGSERIAL           →  NUMBER + SEQUENCE or IDENTITY
```

### Decision Logic

```python
def map_type(pg_type, options) -> (sf_type, rationale):
    """
    Input: PostgreSQL type + metadata
    Output: Snowflake type + reasoning
    
    Considers:
    - Base type
    - Precision/scale for NUMERIC
    - Length for VARCHAR
    - Nullability
    - Default values
    - Identity/sequence info
    """
```

## Data Pipeline Architecture

### Extract Phase

```python
class DataExtractor:
    """
    Extracts data from PostgreSQL tables.
    
    Methods:
    - extract_table_to_csv()   # CSV with gzip compression
    - extract_table_to_parquet() # Parquet with Snappy compression
    
    Features:
    - Server-side cursors (low memory)
    - Chunking (configurable size)
    - JSON serialization
    - NULL handling
    - Progress tracking
    """
```

**Chunking Strategy:**
- Default: 200 MB per chunk
- Configurable: 1-1000 MB
- Row-based chunking (e.g., 100,000 rows)
- Deterministic file naming: `{schema}_{table}_chunk_{num:04d}.{ext}`

### Load Phase

```python
class SnowflakeLoader:
    """
    Loads data into Snowflake.
    
    Methods:
    - upload_file_to_stage()  # PUT command
    - copy_into_table()        # COPY INTO command
    - execute_ddl()            # DDL execution
    
    Features:
    - OAuth authentication
    - Retry logic (exponential backoff)
    - Idempotency (file manifest tracking)
    - MATCH_BY_COLUMN_NAME
    - Error handling
    """
```

**COPY INTO Strategy:**
```sql
COPY INTO {schema}.{table} ({columns})
FROM @{stage}
FILES = ('{file_pattern}')
FILE_FORMAT = {file_format}
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT'
PURGE = FALSE
```

### Parallelism

```python
class MigrationPipeline:
    """
    Orchestrates parallel table migrations.
    
    Uses ThreadPoolExecutor:
    - Configurable workers (1-16)
    - Per-table processing
    - Independent connections
    - Aggregated results
    """
```

**Parallel Execution Model:**
```
Table 1 ─┐
Table 2 ─┤
Table 3 ─┼─► ThreadPoolExecutor (N workers) ─► Snowflake
Table 4 ─┤
Table 5 ─┘
```

## Validation System

### Validation Checks

1. **Row Count Comparison**
   ```sql
   -- PostgreSQL
   SELECT COUNT(*) FROM schema.table;
   
   -- Snowflake
   SELECT COUNT(*) FROM schema.table;
   
   -- Compare results
   ```

2. **NOT NULL Constraints**
   ```sql
   -- For each NOT NULL column:
   SELECT COUNT(*) FROM table WHERE column IS NULL;
   -- Should be 0
   ```

3. **Primary Key Duplicates**
   ```sql
   SELECT pk_columns, COUNT(*)
   FROM table
   GROUP BY pk_columns
   HAVING COUNT(*) > 1;
   -- Should return 0 rows
   ```

4. **JSON Validity**
   ```sql
   SELECT COUNT(*)
   FROM table
   WHERE json_column IS NOT NULL
     AND TRY_PARSE_JSON(json_column) IS NULL;
   -- Should be 0
   ```

## Security Architecture

### Authentication Flow

```
User
  │
  ▼
Okta Authentication
  │
  ├─► Authorization Code
  │
  ▼
Token Exchange
  │
  ├─► Access Token
  │       │
  │       ▼
  │   Migration Agent
  │       │
  │       ▼
  │   Snowflake API
  │   (OAuth Authenticator)
  │
  ▼
Snowflake Session
```

### Credential Handling

**PostgreSQL:**
- Username/password provided by user
- Never logged or stored persistently
- Connection closed after use

**Snowflake:**
- OAuth token from Okta
- No password required
- Token redacted in logs
- Token validation before use

**Redaction System:**
```python
REDACTION_PATTERNS = [
    (r'"password"\s*:\s*"[^"]*"', '"password": "***REDACTED***"'),
    (r'"access_token"\s*:\s*"[^"]*"', '"access_token": "***REDACTED***"'),
    (r'password=[^\s&]+', 'password=***REDACTED***'),
    (r'token=[^\s&]+', 'token=***REDACTED***'),
]
```

### Audit Trail

**Structured Logging (NDJSON):**
```json
{
  "ts": "2024-01-15T10:30:00.123456",
  "run_id": "abc123...",
  "level": "INFO",
  "category": "migration",
  "message": "Table migration completed",
  "objectRef": "public.customers",
  "rows": 1234567,
  "duration_ms": 45230
}
```

## Error Handling

### Retry Strategy

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
def operation():
    # Retries 3 times with exponential backoff
    # Wait: 4s, 8s, 16s (capped at 60s)
    pass
```

### Failure Recovery

**Idempotency:**
- DDL uses `IF NOT EXISTS`
- File names are deterministic
- Track loaded files in manifest
- Safe to re-run entire migration

**Partial Failure:**
- Each table is independent unit of work
- Failed tables can be retried individually
- Successfully migrated tables aren't re-processed

### Error Reporting

```python
{
    "table": "schema.table",
    "status": "failed",
    "error": "Connection timeout",
    "retries": 3,
    "duration_ms": 120000
}
```

## Performance Considerations

### Optimization Strategies

1. **Parallel Processing:**
   - Multiple tables simultaneously
   - Independent database connections
   - Configurable worker count

2. **Chunking:**
   - Reduces memory footprint
   - Enables progress tracking
   - Better fault tolerance

3. **Compression:**
   - GZIP for CSV (70-90% reduction)
   - Snappy for Parquet (50-70% reduction)

4. **Server-Side Cursors:**
   - Low memory usage
   - Stream large result sets
   - No client-side buffering

5. **Batch Operations:**
   - Single COPY command per file
   - Bulk DDL execution
   - Aggregated validation queries

### Scalability

**Horizontal Scaling:**
- Run multiple migration agents
- Different schema subsets per agent
- Shared Snowflake warehouse

**Vertical Scaling:**
- Increase parallelism setting
- Larger warehouse in Snowflake
- More memory for agent process

## Monitoring & Observability

### Metrics Collected

- Tables migrated / total
- Rows processed per second
- Data volume (GB/hour)
- Error rate
- Retry count
- Duration per phase

### Log Levels

- **INFO** - Normal operations
- **WARN** - Non-critical issues
- **ERROR** - Failures requiring attention

### Progress Tracking

Real-time updates include:
- Current phase
- Completion percentage
- Table-level status
- Row counts
- Duration estimates

---

**See also:**
- [Developer Guide](DEVELOPER_GUIDE.md) for code walkthrough
- [Setup Instructions](SETUP.md) for deployment
- [User Guide](USER_GUIDE.md) for usage
