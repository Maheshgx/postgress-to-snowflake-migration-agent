# System and Application Requirements

Complete list of requirements for the PostgreSQL to Snowflake Migration Agent.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Software Requirements](#software-requirements)
3. [Database Requirements](#database-requirements)
4. [Network Requirements](#network-requirements)
5. [Security Requirements](#security-requirements)
6. [Performance Requirements](#performance-requirements)
7. [Functional Requirements](#functional-requirements)

## System Requirements

### Hardware Requirements

#### Minimum Configuration

| Component | Specification |
|-----------|--------------|
| CPU | 2 cores, 2.0 GHz |
| RAM | 4 GB |
| Disk Space | 10 GB free |
| Network | 10 Mbps |

**Suitable for:**
- Testing/development
- Small databases (< 10 GB)
- Single-user scenarios

#### Recommended Configuration

| Component | Specification |
|-----------|--------------|
| CPU | 4-8 cores, 2.5+ GHz |
| RAM | 8-16 GB |
| Disk Space | 50-100 GB free (or 2x source DB size) |
| Network | 100+ Mbps |

**Suitable for:**
- Production migrations
- Medium databases (10-500 GB)
- Multiple concurrent migrations

#### High-Performance Configuration

| Component | Specification |
|-----------|--------------|
| CPU | 8+ cores, 3.0+ GHz |
| RAM | 32+ GB |
| Disk Space | 200+ GB SSD/NVMe |
| Network | 1+ Gbps |

**Suitable for:**
- Large databases (> 500 GB)
- Time-sensitive migrations
- High parallelism (8-16 workers)

### Operating System

**Supported Platforms:**
- Linux (Ubuntu 20.04+, RHEL 8+, Amazon Linux 2)
- macOS 12+
- Windows 10/11 (with WSL2 recommended)

**Recommended:**
- Linux (best performance and compatibility)
- Docker container (platform-independent)

### Storage Requirements

**Disk Space Calculation:**
```
Required Space = (Source DB Size × 1.5) + 10 GB

Components:
- Extracted data files: ~Source DB size
- Compressed files: ~0.3 × Source DB size
- Artifacts/logs: ~1-2 GB
- Application: ~500 MB
- Buffer: 10 GB
```

**Example:**
```
Source DB: 100 GB
Required: (100 × 1.5) + 10 = 160 GB
```

## Software Requirements

### Runtime Dependencies

#### Python (Backend)

**Version:** Python 3.11 or higher

**Required Packages:**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
psycopg2-binary==2.9.9
snowflake-connector-python==3.6.0
pandas==2.1.3
pyarrow==14.0.1
pyyaml==6.0.1
structlog==23.2.0
tenacity==8.2.3
```

**System Libraries (Linux):**
```bash
# Ubuntu/Debian
apt-get install python3-dev libpq-dev build-essential

# RHEL/CentOS
yum install python3-devel postgresql-devel gcc
```

#### Node.js (Frontend)

**Version:** Node.js 18+ and npm 9+

**Required Packages:**
```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "typescript": "^5.2.2",
  "tailwindcss": "^3.3.6",
  "axios": "^1.6.2",
  "@tanstack/react-query": "^5.12.0",
  "lucide-react": "^0.294.0",
  "vite": "^5.0.8"
}
```

### Optional Tools

- **Git** - Version control
- **Docker** - Containerized deployment
- **psql** - PostgreSQL client (debugging)
- **snowsql** - Snowflake CLI (debugging)

## Database Requirements

### PostgreSQL (Source)

**Supported Versions:**
- PostgreSQL 12, 13, 14, 15, 16
- Compatible with cloud providers (AWS RDS, Azure Database, GCP Cloud SQL)

**Required Permissions:**
```sql
-- Minimum read-only access
GRANT CONNECT ON DATABASE {database} TO {user};
GRANT USAGE ON SCHEMA {schema} TO {user};
GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO {user};
GRANT SELECT ON ALL SEQUENCES IN SCHEMA {schema} TO {user};
```

**Recommended User Configuration:**
```sql
CREATE USER migration_user WITH PASSWORD 'secure_password'
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    CONNECTION LIMIT 5;  -- Limit concurrent connections
```

**Database Configuration:**
- `max_connections` ≥ 10 (for migration + existing workload)
- `statement_timeout` = 0 (or high value for large queries)
- `work_mem` ≥ 64MB (for sorting large result sets)

### Snowflake (Target)

**Account Requirements:**
- Active Snowflake account (Standard, Enterprise, or Business Critical)
- Okta External OAuth integration configured
- Valid credit/trial balance

**Warehouse Requirements:**
```sql
-- Recommended initial warehouse
CREATE WAREHOUSE MIGRATION_WH
    WAREHOUSE_SIZE = 'MEDIUM'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = FALSE
    MAX_CLUSTER_COUNT = 1;
```

**Role Permissions:**
```sql
GRANT USAGE ON WAREHOUSE {warehouse} TO ROLE {role};
GRANT CREATE DATABASE ON ACCOUNT TO ROLE {role};
GRANT CREATE SCHEMA ON DATABASE {database} TO ROLE {role};
GRANT CREATE TABLE ON SCHEMA {schema} TO ROLE {role};
GRANT CREATE STAGE ON SCHEMA {schema} TO ROLE {role};
GRANT CREATE FILE FORMAT ON SCHEMA {schema} TO ROLE {role};
GRANT CREATE SEQUENCE ON SCHEMA {schema} TO ROLE {role};
GRANT CREATE VIEW ON SCHEMA {schema} TO ROLE {role};
```

**Storage Requirements:**
- Available storage ≥ Source DB size
- Consider Fail-safe (7 days) and Time Travel storage overhead

### Database Connectivity

**PostgreSQL Connection:**
- TCP/IP enabled
- SSL/TLS recommended
- Connection string format: `postgresql://user:pass@host:port/database`

**Snowflake Connection:**
- HTTPS access (port 443)
- OAuth token-based authentication
- Account identifier: `{account}.{region}.{cloud}`

## Network Requirements

### Connectivity

**Required Connections:**
```
Migration Agent → PostgreSQL (port 5432)
Migration Agent → Snowflake (port 443 HTTPS)
Migration Agent → Okta (port 443 HTTPS)
User Browser → Migration Agent (port 3000/8000)
```

**Bandwidth Requirements:**

| Database Size | Minimum | Recommended |
|--------------|---------|-------------|
| < 10 GB      | 10 Mbps | 50 Mbps     |
| 10-100 GB    | 50 Mbps | 100 Mbps    |
| 100-500 GB   | 100 Mbps| 500 Mbps    |
| > 500 GB     | 500 Mbps| 1 Gbps      |

### Firewall Rules

**Inbound Rules:**
```
Allow TCP 8000 from {allowed_ips}  # API server
Allow TCP 3000 from {allowed_ips}  # Frontend dev server
```

**Outbound Rules:**
```
Allow TCP 5432 to {postgres_host}     # PostgreSQL
Allow TCP 443 to *.snowflakecomputing.com  # Snowflake
Allow TCP 443 to {okta_domain}.okta.com    # Okta
```

### Network Latency

**Acceptable Latency:**
- PostgreSQL: < 50ms (same region recommended)
- Snowflake: < 100ms (same cloud region recommended)
- User to Agent: < 200ms

**Optimization:**
- Deploy agent close to PostgreSQL (minimize extract latency)
- Use Snowflake region close to PostgreSQL
- Consider VPN/VPC peering for cloud deployments

## Security Requirements

### Authentication

**PostgreSQL:**
- Username/password authentication
- Certificate-based authentication (optional)
- md5, scram-sha-256, or certificate auth methods

**Snowflake:**
- Okta External OAuth (required)
- No password-based authentication
- Token-based, time-limited access

**Application:**
- No built-in user authentication (deploy behind auth proxy if needed)
- HTTPS recommended for web interface
- CORS restrictions for API access

### Authorization

**PostgreSQL User:**
- READ-ONLY access required
- No DDL permissions needed
- No DML permissions needed
- Schema-level access control

**Snowflake Role:**
- CREATE permissions on target database
- USAGE on warehouse
- No ACCOUNTADMIN required
- Specific role for migration workload

### Data Protection

**In Transit:**
- PostgreSQL: SSL/TLS recommended
- Snowflake: HTTPS (TLS 1.2+) enforced
- Application: HTTPS recommended

**At Rest:**
- Temporary files: Encrypted file system recommended
- Snowflake: Automatic encryption (AES-256)
- Artifacts: Stored locally with OS-level permissions

**Audit & Compliance:**
- Complete audit trail in NDJSON logs
- Credential redaction in logs
- No persistent storage of credentials
- Compliance with GDPR, HIPAA (via Snowflake)

## Performance Requirements

### Migration Speed

**Expected Performance:**

| Database Size | Parallelism | Expected Duration |
|--------------|-------------|-------------------|
| 1 GB         | 2-4         | 5-15 minutes      |
| 10 GB        | 4-8         | 30-90 minutes     |
| 100 GB       | 8-16        | 3-8 hours         |
| 500 GB       | 8-16        | 12-36 hours       |
| 1 TB         | 16          | 24-72 hours       |

**Factors Affecting Speed:**
- Network bandwidth
- PostgreSQL disk I/O
- Snowflake warehouse size
- Table sizes and distribution
- Data types and complexity
- Parallelism setting

### Resource Utilization

**CPU:**
- Analysis phase: 30-50% average
- Extraction phase: 50-70% average
- Load phase: 40-60% average
- Peaks during parallel operations

**Memory:**
- Base usage: 500 MB
- Per worker thread: 200-500 MB
- Total = Base + (Workers × Per-Worker)
- Example: 500 + (8 × 300) = 2.9 GB

**Disk I/O:**
- Write speed ≥ 100 MB/s recommended
- Read speed ≥ 50 MB/s (from PostgreSQL network)
- SSD/NVMe strongly recommended

**Network:**
- PostgreSQL → Agent: 10-100 MB/s
- Agent → Snowflake: 10-100 MB/s
- Total bandwidth = Extract + Load (parallel)

## Functional Requirements

### Core Functionality

**Must Have:**
- ✅ PostgreSQL introspection (all object types)
- ✅ Type mapping (comprehensive)
- ✅ DDL generation (Snowflake syntax)
- ✅ Data extraction (CSV/Parquet)
- ✅ Data loading (COPY INTO)
- ✅ Progress tracking (real-time)
- ✅ Validation (row counts, constraints)
- ✅ Audit logging (structured)
- ✅ Error handling (retry, recovery)
- ✅ Dry run mode (plan without execution)

**Should Have:**
- Incremental migration (future)
- Resume from failure (partial)
- Multi-schema parallelism
- Custom type mappings
- Webhook notifications (future)

**Could Have:**
- Delta/CDC migration (future)
- Bi-directional sync (future)
- GUI-based type mapping editor
- Built-in data quality rules
- Automated performance tuning

### Supported Objects

**Fully Supported:**
- Tables (all types)
- Columns (all standard types)
- Primary keys
- Unique constraints
- NOT NULL constraints
- Sequences
- Default values
- Comments

**Partially Supported:**
- Foreign keys (documented, not enforced)
- Check constraints (documented)
- Views (SQL requires review)
- Materialized views (data only)
- Indexes (cluster keys suggested)

**Not Supported:**
- Triggers (manual conversion required)
- Functions/Procedures (manual conversion)
- Extensions (case-by-case)
- Row-level security policies
- Inheritance/Partitioning (flattened)

### Data Type Support

**Fully Supported:**
- All numeric types
- All string types
- All date/time types
- BOOLEAN
- JSON/JSONB → VARIANT
- BYTEA → BINARY
- UUID → VARCHAR

**Requires Review:**
- Arrays → VARIANT
- Enums → VARCHAR
- Composite types → VARCHAR/VARIANT
- Geometric types → VARCHAR
- Network address types → VARCHAR

### Scalability Limits

**Tested Limits:**
- Database size: Up to 2 TB
- Table count: Up to 10,000 tables
- Largest table: Up to 500 GB
- Column count: Up to 1,000 per table
- Parallelism: Up to 16 workers

**Theoretical Limits:**
- Constrained by system resources
- Snowflake: 10,000+ tables per schema
- PostgreSQL: Limited by connection pool

## Browser Requirements

### Supported Browsers

| Browser | Minimum Version |
|---------|----------------|
| Chrome  | 100+           |
| Firefox | 100+           |
| Safari  | 15+            |
| Edge    | 100+           |

**Features Required:**
- JavaScript enabled
- WebSocket support (for future real-time updates)
- LocalStorage (for session state)
- Fetch API

---

**Next Steps:**
- Review [Setup Instructions](SETUP.md) for installation
- See [User Guide](USER_GUIDE.md) for usage
- Check [Architecture](ARCHITECTURE.md) for technical details
