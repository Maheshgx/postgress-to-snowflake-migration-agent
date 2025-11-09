# Getting Started Guide

Complete step-by-step guide to configure and use the PostgreSQL to Snowflake Migration Agent.

## Quick Navigation

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Okta OAuth Setup](#3-okta-oauth-setup)
4. [Snowflake Configuration](#4-snowflake-configuration)
5. [PostgreSQL Configuration](#5-postgresql-configuration)
6. [Starting the Application](#6-starting-the-application)
7. [Running Your First Migration](#7-running-your-first-migration)
8. [Understanding Results](#8-understanding-results)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites

### Required Software

Check your installations:
```bash
python --version     # Need 3.11+
node --version       # Need 18+
npm --version
git --version
docker --version     # Optional
```

### Required Access
- ✅ PostgreSQL database (source) with SELECT permissions
- ✅ Snowflake account with database creation rights
- ✅ Okta account with OAuth admin access
- ✅ Network access to both databases

---

## 2. Installation

### 2.1 Clone and Setup

```bash
# Clone repository
git clone https://github.com/Maheshgx/postgress-to-snowflake-migration-agent.git
cd postgress-to-snowflake-migration-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Create required directories
mkdir -p artifacts temp logs
```

### 2.2 Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Generate secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Edit .env file with your settings
```

**Edit `.env`:**
```bash
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
SECRET_KEY=<paste generated key here>
ARTIFACTS_PATH=./artifacts
TEMP_PATH=./temp
```

---

## 3. Okta OAuth Setup

### 3.1 Create OAuth Application

1. Login to Okta Admin Console: `https://your-domain.okta.com/admin`
2. Go to **Applications** → **Create App Integration**
3. Select: **OIDC** and **Web Application**
4. Configure:
   - **Name**: Snowflake Migration Agent
   - **Grant types**: ☑ Authorization Code, ☑ Client Credentials, ☑ Refresh Token
   - **Redirect URI**: `https://your-snowflake.snowflakecomputing.com/oauth/authorize`
5. Save and note **Client ID** and **Client Secret**

### 3.2 Get Access Token

```bash
curl --request POST \
  --url https://your-domain.okta.com/oauth2/default/v1/token \
  --header 'content-type: application/x-www-form-urlencoded' \
  --data 'grant_type=client_credentials' \
  --data 'client_id=YOUR_CLIENT_ID' \
  --data 'client_secret=YOUR_CLIENT_SECRET' \
  --data 'scope=session:role:MIGRATION_ROLE'
```

**Save the `access_token` from response!**

---

## 4. Snowflake Configuration

Run these SQL commands in Snowflake:

### 4.1 Create Security Integration

```sql
USE ROLE ACCOUNTADMIN;

CREATE SECURITY INTEGRATION okta_oauth
    TYPE = EXTERNAL_OAUTH
    ENABLED = TRUE
    EXTERNAL_OAUTH_TYPE = OKTA
    EXTERNAL_OAUTH_ISSUER = 'https://your-domain.okta.com/oauth2/default'
    EXTERNAL_OAUTH_JWS_KEYS_URL = 'https://your-domain.okta.com/oauth2/default/v1/keys'
    EXTERNAL_OAUTH_AUDIENCE_LIST = ('https://your-snowflake.snowflakecomputing.com')
    EXTERNAL_OAUTH_TOKEN_USER_MAPPING_CLAIM = 'sub'
    EXTERNAL_OAUTH_SNOWFLAKE_USER_MAPPING_ATTRIBUTE = 'EMAIL_ADDRESS'
    EXTERNAL_OAUTH_ANY_ROLE_MODE = 'ENABLE';
```

### 4.2 Create Migration Role and Warehouse

```sql
-- Create role
CREATE ROLE MIGRATION_ROLE;
GRANT ROLE MIGRATION_ROLE TO USER "your-email@company.com";

-- Create warehouse
CREATE WAREHOUSE MIGRATION_WH
    WAREHOUSE_SIZE = 'MEDIUM'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE;

GRANT USAGE ON WAREHOUSE MIGRATION_WH TO ROLE MIGRATION_ROLE;
```

### 4.3 Create Target Database and Stage

```sql
-- Create database and schema
CREATE DATABASE TARGET_DB;
USE DATABASE TARGET_DB;
CREATE SCHEMA PUBLIC;

-- Grant privileges
GRANT CREATE DATABASE ON ACCOUNT TO ROLE MIGRATION_ROLE;
GRANT CREATE SCHEMA ON DATABASE TARGET_DB TO ROLE MIGRATION_ROLE;
GRANT CREATE TABLE ON SCHEMA TARGET_DB.PUBLIC TO ROLE MIGRATION_ROLE;
GRANT CREATE STAGE ON SCHEMA TARGET_DB.PUBLIC TO ROLE MIGRATION_ROLE;
GRANT CREATE FILE FORMAT ON SCHEMA TARGET_DB.PUBLIC TO ROLE MIGRATION_ROLE;

-- Create stage and file format
USE SCHEMA TARGET_DB.PUBLIC;

CREATE STAGE MIGRATION_STAGE ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');

CREATE FILE FORMAT MIGRATION_CSV_FORMAT
    TYPE = 'CSV'
    COMPRESSION = 'GZIP'
    FIELD_DELIMITER = ','
    SKIP_HEADER = 1
    NULL_IF = ('\\N', 'NULL', 'null', '');
```

**Note these values:**
- Account: `abc12345.us-east-1`
- Warehouse: `MIGRATION_WH`
- Database: `TARGET_DB`
- Role: `MIGRATION_ROLE`
- Stage: `MIGRATION_STAGE`
- File Format: `MIGRATION_CSV_FORMAT`

---

## 5. PostgreSQL Configuration

### 5.1 Create Migration User (Recommended)

```sql
-- Create user
CREATE USER migration_user WITH PASSWORD 'secure_password';

-- Grant permissions
GRANT CONNECT ON DATABASE your_database TO migration_user;
GRANT USAGE ON SCHEMA public TO migration_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO migration_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO migration_user;
```

### 5.2 Test Connection

```bash
psql -h your-host -p 5432 -U migration_user -d your_database
```

**Note these values:**
- Host: `your-postgres-host.example.com`
- Port: `5432`
- Database: `your_database`
- Username: `migration_user`
- Password: `[your password]`
- Schemas: `["public"]` or `["*"]` for all

---

## 6. Starting the Application

### 6.1 Start Backend (Terminal 1)

```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO: Uvicorn running on http://0.0.0.0:8000
INFO: Application startup complete.
```

### 6.2 Verify Backend

```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy","version":"1.0.0",...}
```

### 6.3 Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

Expected output:
```
  VITE ready in 1234 ms
  ➜  Local:   http://localhost:5173/
```

### 6.4 Access Application

Open browser: **http://localhost:5173**

---

## 7. Running Your First Migration

### 7.1 Fill in Configuration Form

**PostgreSQL Section:**
```
Host: your-postgres-host
Port: 5432
Database: your_database
Username: migration_user
Password: [your password]
Schemas: ["public"]
```

**Snowflake Section:**
```
Account: abc12345.us-east-1
Warehouse: MIGRATION_WH
Database: TARGET_DB
Schema: PUBLIC
Default Role: MIGRATION_ROLE
Stage: MIGRATION_STAGE
File Format: MIGRATION_CSV_FORMAT
```

**OAuth Section:**
```
Access Token: [Paste token from Step 3.2]
```

**Preferences:**
```
Format: CSV
Max Chunk MB: 200
Parallelism: 4
Case Style: UPPER
Dry Run: ☑ YES (Always start with dry run!)
```

### 7.2 Test Connections

Click **"Test Connections"** button

Expected:
- ✅ PostgreSQL: Connected
- ✅ Snowflake: Connected

### 7.3 Run Dry Run

1. Ensure **"Dry Run"** is checked
2. Click **"Start Migration"**
3. Monitor progress:
   - Phase 1: ANALYZING (25%)
   - Phase 2: PLANNING (50%)
   - Phase 3: GENERATING (100%)

### 7.4 Download and Review Artifacts

Click **"View Artifacts"** to download:
- `analysis_report.json` - Database analysis
- `snowflake_objects.sql` - Generated DDL
- `mapping_decisions.yml` - Type mappings
- `improvement_recommendations.md` - Optimization tips
- `summary.md` - Migration summary

### 7.5 Run Full Migration

After reviewing dry run:

1. **Backup your database first!**
   ```bash
   pg_dump -h your-host -U your-user -d your_database -F c -f backup.dump
   ```

2. **Uncheck "Dry Run"** in the web UI
3. Click **"Start Migration"**
4. Monitor real-time progress for each table
5. Wait for completion (time varies by size)

---

## 8. Understanding Results

### 8.1 Migration Progress

Monitor these phases:
- **ANALYZING**: Reading PostgreSQL schema
- **PLANNING**: Generating Snowflake DDL
- **EXECUTING**: Creating objects and loading data
- **VALIDATING**: Checking data quality
- **COMPLETED**: Migration finished

### 8.2 Table Status Indicators

- ✅ **Completed**: Table migrated successfully
- ⏳ **In Progress**: Currently loading data
- ❌ **Failed**: Error occurred (check logs)
- ⏸️ **Pending**: Waiting in queue

### 8.3 Validation Results

Check these after migration:
```
Row Count Verification:
✅ customers: Source=150K, Target=150K (Match)
✅ orders: Source=500K, Target=500K (Match)

NOT NULL Constraints: ✅ Passed
Primary Key Duplicates: ✅ None found
JSON Validity: ✅ All valid
```

### 8.4 Post-Migration Checks in Snowflake

```sql
-- Verify row counts
SELECT 'customers' AS table_name, COUNT(*) FROM PUBLIC.CUSTOMERS
UNION ALL
SELECT 'orders', COUNT(*) FROM PUBLIC.ORDERS;

-- Check data sample
SELECT * FROM PUBLIC.CUSTOMERS LIMIT 10;

-- Verify structure
DESC TABLE PUBLIC.CUSTOMERS;
SHOW TABLES IN SCHEMA PUBLIC;
```

---

## 9. Troubleshooting

### Connection Errors

**Problem**: Can't connect to PostgreSQL
```bash
# Test manually
psql -h your-host -U your-user -d your-database

# Check firewall/network
ping your-host
telnet your-host 5432
```

**Problem**: Can't connect to Snowflake
- Verify account identifier format
- Check OAuth token hasn't expired (generate new one)
- Verify security integration: `DESC SECURITY INTEGRATION okta_oauth;`

### OAuth Token Expired

```bash
# Generate new token (expires in ~1 hour)
curl --request POST \
  --url https://your-domain.okta.com/oauth2/default/v1/token \
  --header 'content-type: application/x-www-form-urlencoded' \
  --data 'grant_type=client_credentials' \
  --data 'client_id=YOUR_CLIENT_ID' \
  --data 'client_secret=YOUR_CLIENT_SECRET' \
  --data 'scope=session:role:MIGRATION_ROLE'
```

### Permission Denied

**PostgreSQL**:
```sql
GRANT SELECT ON ALL TABLES IN SCHEMA public TO migration_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO migration_user;
```

**Snowflake**:
```sql
GRANT CREATE TABLE ON SCHEMA TARGET_DB.PUBLIC TO ROLE MIGRATION_ROLE;
GRANT USAGE ON WAREHOUSE MIGRATION_WH TO ROLE MIGRATION_ROLE;
```

### Frontend Won't Start

```bash
# Port already in use
lsof -ti:5173 | xargs kill -9

# Or use different port
npm run dev -- --port 5174
```

### Migration Hangs

```bash
# Check backend logs
tail -f logs/run_log.ndjson

# Check Snowflake warehouse is running
# In Snowflake:
SHOW WAREHOUSES LIKE 'MIGRATION_WH';
ALTER WAREHOUSE MIGRATION_WH RESUME;
```

### Row Count Mismatch

```sql
-- Check COPY errors in Snowflake
SELECT * FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
    TABLE_NAME=>'YOUR_TABLE',
    START_TIME=>DATEADD(hours, -1, CURRENT_TIMESTAMP())
));

-- Look for rejected rows
SELECT * FROM TABLE(VALIDATE(YOUR_TABLE, JOB_ID=>'<job_id>'));
```

### Application Logs

```bash
# Backend logs (structured JSON)
tail -f logs/run_log.ndjson | jq .

# Backend console
# See Terminal 1 where uvicorn is running

# Frontend console
# Open browser Developer Tools (F12) → Console tab
```

---

## Additional Resources

- **[User Guide](USER_GUIDE.md)** - Detailed usage instructions
- **[Developer Guide](DEVELOPER_GUIDE.md)** - Code walkthrough
- **[Setup Instructions](SETUP.md)** - Advanced setup
- **[Dev Container Guide](DEVCONTAINER_GUIDE.md)** - Container setup
- **[Architecture](ARCHITECTURE.md)** - System design
- **API Docs**: http://localhost:8000/docs (when running)

---

## Quick Reference Card

### Configuration Summary

| Component | Value | Where to Get |
|-----------|-------|--------------|
| PostgreSQL Host | your-host.example.com | Your DBA |
| PostgreSQL Port | 5432 | Standard port |
| PostgreSQL DB | your_database | Your database name |
| Snowflake Account | abc12345.us-east-1 | Snowflake admin console |
| Snowflake Warehouse | MIGRATION_WH | Created in Step 4.2 |
| Snowflake Database | TARGET_DB | Created in Step 4.3 |
| Snowflake Role | MIGRATION_ROLE | Created in Step 4.2 |
| OAuth Token | eyJhbGc... | Generated in Step 3.2 |

### Common Commands

```bash
# Start backend
cd backend && python -m uvicorn main:app --reload --port 8000

# Start frontend
cd frontend && npm run dev

# Test health
curl http://localhost:8000/health

# View logs
tail -f logs/run_log.ndjson

# Backup PostgreSQL
pg_dump -h host -U user -d db -F c -f backup.dump

# Generate OAuth token
curl -X POST https://your-domain.okta.com/oauth2/default/v1/token \
  -H 'content-type: application/x-www-form-urlencoded' \
  -d 'grant_type=client_credentials' \
  -d 'client_id=YOUR_ID' \
  -d 'client_secret=YOUR_SECRET' \
  -d 'scope=session:role:MIGRATION_ROLE'
```

---

**Ready to migrate!** Follow the steps in order, and always start with a dry run. For issues, check the Troubleshooting section or review logs.
