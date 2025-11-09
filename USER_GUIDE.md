# User Guide - PostgreSQL to Snowflake Migration Agent

## Table of Contents

1. [Getting Started](#getting-started)
2. [Understanding the Interface](#understanding-the-interface)
3. [Configuration](#configuration)
4. [Running Migrations](#running-migrations)
5. [Monitoring Progress](#monitoring-progress)
6. [Reviewing Results](#reviewing-results)
7. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites Checklist

Before starting a migration, ensure you have:

- ✅ PostgreSQL database credentials (host, port, database, username, password)
- ✅ List of schemas to migrate (or use `*` for all non-system schemas)
- ✅ Snowflake account identifier
- ✅ Snowflake warehouse name (should be running)
- ✅ Snowflake target database name
- ✅ Snowflake role with appropriate permissions
- ✅ **Okta External OAuth access token** for Snowflake
- ✅ Network connectivity between migration agent and both databases

### First-Time Setup

1. **Access the Application**
   - Open your web browser
   - Navigate to `http://localhost:3000` (or your configured URL)
   - You should see the migration agent interface

2. **Prepare Snowflake Objects**
   ```sql
   -- Create database (if doesn't exist)
   CREATE DATABASE IF NOT EXISTS MY_DATABASE;
   
   -- Create stage
   CREATE STAGE IF NOT EXISTS MY_DATABASE.PUBLIC.MIGRATION_STAGE;
   
   -- Create file format
   CREATE FILE FORMAT IF NOT EXISTS MY_DATABASE.PUBLIC.MIGRATION_CSV_FORMAT
       TYPE = 'CSV'
       COMPRESSION = 'GZIP'
       FIELD_DELIMITER = ','
       SKIP_HEADER = 1
       FIELD_OPTIONALLY_ENCLOSED_BY = '"'
       TRIM_SPACE = TRUE;
   ```

## Understanding the Interface

### Navigation Tabs

The interface has three main tabs:

1. **Configuration** - Set up source, target, and migration preferences
2. **Migration Progress** - Monitor real-time migration status
3. **Artifacts** - Download generated reports and DDL files

### Status Indicators

| Status | Meaning |
|--------|---------|
| 🟡 Pending | Migration queued but not started |
| 🔵 Analyzing | Introspecting PostgreSQL database |
| 🟣 Planning | Generating Snowflake DDL and migration plan |
| 🟠 Awaiting Confirmation | Plan ready; waiting for approval |
| 🟢 Executing | Migrating data |
| 🟣 Validating | Running post-migration checks |
| ✅ Completed | Migration finished successfully |
| ❌ Failed | Migration encountered errors |

## Configuration

### PostgreSQL Source Configuration

**Required Fields:**

- **Host** - PostgreSQL server hostname or IP (e.g., `localhost`, `db.example.com`)
- **Port** - PostgreSQL port (default: `5432`)
- **Database** - Source database name
- **Username** - PostgreSQL user with read access
- **Password** - User password (will be redacted in logs)

**Schema Selection:**

- **`*`** - Migrates all non-system schemas (excludes `pg_catalog`, `information_schema`)
- **Specific schemas** - Comma-separated list (e.g., `public,sales,marketing`)

**Example:**
```
Host: prod-db.example.com
Port: 5432
Database: ecommerce
Username: migration_user
Password: ••••••••
Schemas: public,analytics
```

### Snowflake Target Configuration

**Required Fields:**

- **Account** - Snowflake account identifier (e.g., `abc12345.us-east-1`)
- **Warehouse** - Warehouse name (must exist and be running)
- **Database** - Target database (will be created if doesn't exist)
- **Role** - Snowflake role with CREATE privileges
- **Schema** - Default schema (default: `PUBLIC`)
- **Stage** - Named stage for file uploads
- **File Format** - Named file format for COPY commands

**Okta OAuth Token:**

- Obtain from your Okta administrator
- Must have Snowflake integration configured
- Token should have appropriate Snowflake access
- Token expires - ensure it's valid for migration duration

**Example:**
```
Account: xy12345.us-west-2
Warehouse: MIGRATION_WH
Database: ECOMMERCE_PROD
Role: MIGRATION_ROLE
Schema: PUBLIC
Stage: MIGRATION_STAGE
File Format: MIGRATION_CSV_FORMAT
Access Token: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Migration Preferences

**Data Format:**

- **CSV** - Compressed CSV files (gzipped)
  - Pros: Universal compatibility, text-based
  - Cons: Larger file sizes, slower for large datasets
  
- **Parquet** - Columnar format (Snappy compression)
  - Pros: Better compression, faster loading, preserves data types
  - Cons: Binary format

**Max Chunk Size (MB):**
- Default: `200`
- Range: `1-1000`
- Larger chunks = fewer files, but higher memory usage
- Smaller chunks = more files, better parallelism

**Parallelism:**
- Default: `4`
- Range: `1-16`
- Number of tables to migrate concurrently
- Higher = faster (if resources available)
- Consider database load and network bandwidth

**Case Style:**
- **UPPER** - All identifiers in UPPERCASE (Snowflake default)
- **LOWER** - All identifiers in lowercase
- **PRESERVE** - Keep original PostgreSQL casing (may require quoting)

**Use IDENTITY for Serial:**
- ✅ Checked (recommended) - PostgreSQL serials become Snowflake IDENTITY
- ❌ Unchecked - Uses SEQUENCE + DEFAULT

**Dry Run:**
- ✅ Checked - Analyze and plan only, no data migration
- ❌ Unchecked - Full migration execution

## Running Migrations

### Test Connections First

Always test connections before starting migration:

1. Fill in all configuration fields
2. Click **"Test Connections"** button
3. Wait for results:
   - ✅ Both connections successful → Proceed
   - ❌ PostgreSQL failed → Check credentials, network, firewall
   - ❌ Snowflake failed → Check OAuth token, account identifier, warehouse status

### Dry Run (Recommended First)

1. Check **"Dry Run"** option
2. Click **"Start Migration"**
3. Wait for analysis to complete (can take several minutes for large databases)
4. Review generated artifacts:
   - Check DDL in `snowflake_objects.sql`
   - Review type mappings in `mapping_decisions.yml`
   - Read recommendations in `improvement_recommendations.md`
5. If satisfied, run again without dry run

### Full Migration

1. Uncheck **"Dry Run"** option
2. Click **"Start Migration"**
3. Migration proceeds through phases:
   - **Analyzing** - Introspecting PostgreSQL (1-5 min)
   - **Planning** - Generating Snowflake objects (1-2 min)
   - **Executing** - Creating objects and loading data (varies)
   - **Validating** - Running data quality checks (1-5 min)

### Understanding Phases

**Phase 1: Analyze**
- Connects to PostgreSQL
- Queries `pg_catalog` and `information_schema`
- Gathers table structures, constraints, indexes
- Calculates volumetrics (row counts, sizes)
- Identifies special types (JSON, arrays, etc.)

**Phase 2: Plan**
- Maps PostgreSQL types to Snowflake equivalents
- Generates DDL for all objects
- Creates load plan with parallelism
- Produces validation SQL queries
- Generates improvement recommendations

**Phase 3: Execute** (only if confirmed)
- Creates Snowflake database/schemas
- Creates tables, sequences, views
- Creates stage and file format
- Extracts data from PostgreSQL
- Uploads files to Snowflake stage
- Executes COPY INTO commands
- Tracks progress per table

**Phase 4: Validate**
- Compares row counts
- Checks NOT NULL constraints
- Scans for primary key duplicates
- Validates JSON structure
- Reports pass/fail for each check

## Monitoring Progress

### Real-Time Updates

The progress view updates every 2 seconds with:

- Overall completion percentage
- Current phase and operation
- Tables completed vs. total
- Per-table status with row counts and duration

### Table Status Indicators

| Icon | Status | Description |
|------|--------|-------------|
| ✅ | Completed | Table migrated successfully |
| ❌ | Failed | Migration error occurred |
| ⏱️ | In Progress | Currently processing |
| ⏳ | Pending | Waiting in queue |

### Interpreting Results

**Successful Table:**
```
Schema: public
Table: customers
Status: ✅ completed
Rows: 1,234,567
Duration: 45.23s
```

**Failed Table:**
```
Schema: public
Table: orders
Status: ❌ failed
Error: Connection timeout
Retries: 3
```

## Reviewing Results

### Generated Artifacts

After migration, download and review these files:

1. **summary.md** ⭐ **Start here**
   - Executive summary
   - Migration statistics
   - Validation results
   - Post-migration checklist
   - Next steps

2. **analysis_report.json**
   - Complete PostgreSQL metadata
   - Table structures, constraints, indexes
   - Volumetrics and statistics
   - Compatibility flags

3. **snowflake_objects.sql**
   - All DDL statements
   - Database, schemas, tables, views
   - Sequences, stages, file formats
   - Comments with PostgreSQL references

4. **mapping_decisions.yml**
   - Per-column type mappings
   - Rationale for each decision
   - Nullable, default, identity flags

5. **improvement_recommendations.md**
   - Warehouse sizing suggestions
   - Cluster key candidates
   - Performance optimization tips
   - Security and governance notes

6. **post_migration_checks.sql**
   - Validation queries to run manually
   - Row count checks
   - Constraint validation SQL
   - Data quality queries

7. **run_log.ndjson**
   - Complete audit trail
   - Newline-delimited JSON logs
   - All operations with timestamps
   - Errors and warnings

### Validation Results

The summary includes validation checks:

**Row Count Validation:**
```
✅ PASS: public.customers (1,234,567 rows match)
✅ PASS: public.orders (5,678,901 rows match)
❌ FAIL: public.products (PG: 10,000, SF: 9,999)
```

**NOT NULL Violations:**
```
✅ PASS: All NOT NULL constraints satisfied
```

**Primary Key Duplicates:**
```
✅ PASS: No duplicate primary keys found
```

**JSON Validity:**
```
⚠️ WARN: public.metadata.settings has 3 invalid JSON values
```

### Post-Migration Checklist

Use the checklist in `summary.md`:

- [ ] Review validation results
- [ ] Test application connectivity
- [ ] Verify user permissions
- [ ] Run sample queries
- [ ] Check data quality
- [ ] Test foreign key relationships
- [ ] Review performance
- [ ] Set up monitoring
- [ ] Update connection strings
- [ ] Plan cutover

## Troubleshooting

### Common Issues

**Connection Failed**

*Symptom:* "Failed to connect to PostgreSQL/Snowflake"

*Solutions:*
- Verify credentials are correct
- Check network connectivity (`ping`, `telnet`)
- Verify firewall rules allow connection
- For Snowflake: Check OAuth token is valid
- For Snowflake: Ensure warehouse is running

**OAuth Token Expired**

*Symptom:* "Authentication failed" or "Invalid token"

*Solution:*
- Obtain a fresh token from Okta
- Tokens typically expire after 1 hour
- Contact your Okta administrator

**Table Migration Failed**

*Symptom:* Individual table shows ❌ failed status

*Solutions:*
- Check error message in table details
- Review `run_log.ndjson` for stack trace
- Common causes:
  - Data type incompatibility
  - Constraint violation
  - Disk space exhausted
  - Network timeout

**Row Count Mismatch**

*Symptom:* Validation shows different row counts

*Investigation:*
1. Check if source data changed during migration
2. Look for failed COPY commands in logs
3. Manually query both databases:
   ```sql
   -- PostgreSQL
   SELECT COUNT(*) FROM schema.table;
   
   -- Snowflake
   SELECT COUNT(*) FROM schema.table;
   ```
4. Review COPY command results in Snowflake query history

**Out of Memory**

*Symptom:* "MemoryError" or process crashes

*Solutions:*
- Reduce `max_chunk_mb` setting
- Reduce `parallelism` setting
- Increase available system memory
- Process largest tables separately

**Stage Full**

*Symptom:* "No space left" or stage quota exceeded

*Solution:*
- Clean up stage after successful loads:
  ```sql
  REMOVE @MIGRATION_STAGE;
  ```
- Use separate stages for different migrations

### Getting Help

1. **Review Logs**
   - Download `run_log.ndjson`
   - Search for "ERROR" or "FAIL"
   - Check timestamps around failure

2. **Check Documentation**
   - Review this guide
   - Check `ARCHITECTURE.md` for technical details
   - See `DEVELOPER_GUIDE.md` for advanced topics

3. **Common SQL for Debugging**

```sql
-- Snowflake: Check warehouse status
SHOW WAREHOUSES LIKE 'MIGRATION_WH';

-- Snowflake: Check stage contents
LIST @MIGRATION_STAGE;

-- Snowflake: View recent queries
SELECT * FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY())
WHERE QUERY_TEXT LIKE '%COPY INTO%'
ORDER BY START_TIME DESC
LIMIT 10;

-- Snowflake: Check table row counts
SELECT 
    table_schema,
    table_name,
    row_count
FROM information_schema.tables
WHERE table_schema = 'PUBLIC'
ORDER BY table_name;

-- PostgreSQL: Check connection limit
SELECT count(*) FROM pg_stat_activity;
SHOW max_connections;
```

4. **Report Issues**
   - Open GitHub issue with:
     - Migration configuration (redact credentials)
     - Error messages from logs
     - Relevant excerpts from `run_log.ndjson`
     - PostgreSQL and Snowflake versions

### Best Practices

1. **Always run dry run first** - Review plan before execution
2. **Test on small dataset** - Validate process with subset
3. **Monitor system resources** - Watch CPU, memory, disk
4. **Use off-peak hours** - Minimize impact on production
5. **Take backups** - Snapshot source before migration
6. **Validate thoroughly** - Don't skip validation checks
7. **Document decisions** - Keep notes on customizations
8. **Plan rollback** - Have contingency if issues arise

---

**Need more help?** Check the [Developer Guide](DEVELOPER_GUIDE.md) or open an issue on GitHub.
