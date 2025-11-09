# Setup Instructions

Complete guide to installing and configuring the PostgreSQL to Snowflake Migration Agent.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Okta External OAuth Setup](#okta-external-oauth-setup)
4. [PostgreSQL Configuration](#postgresql-configuration)
5. [Snowflake Configuration](#snowflake-configuration)
6. [Application Configuration](#application-configuration)
7. [Verification](#verification)

## System Requirements

### Hardware

**Minimum:**
- CPU: 2 cores
- RAM: 4 GB
- Disk: 10 GB free space

**Recommended:**
- CPU: 4+ cores
- RAM: 8+ GB
- Disk: 50+ GB free space (depends on database size)
- Network: 100 Mbps or higher

### Software

**Required:**
- Python 3.11 or higher
- Node.js 18 or higher
- npm 9 or higher
- Git

**Optional:**
- PostgreSQL client tools (`psql`)
- Snowflake CLI (`snowsql`)

### Network Requirements

The migration agent needs network access to:
- PostgreSQL database (typically port 5432)
- Snowflake account (port 443 HTTPS)
- Okta (for OAuth token exchange, port 443)

## Installation

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd "Postgress to Snowflake MIgration Agent"
```

### Step 2: Backend Setup

```bash
# Create Python virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; import psycopg2; import snowflake.connector; print('Backend dependencies OK')"
```

### Step 3: Frontend Setup

```bash
cd frontend

# Install Node.js dependencies
npm install

# Build frontend (optional, for production)
npm run build

cd ..
```

### Step 4: Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

## Okta External OAuth Setup

### Prerequisites

- Okta account with admin access
- Snowflake account
- Permission to create OAuth integrations in both systems

### Configure Snowflake OAuth Integration

1. **Create Security Integration in Snowflake**

```sql
CREATE SECURITY INTEGRATION okta_oauth
    TYPE = EXTERNAL_OAUTH
    ENABLED = TRUE
    EXTERNAL_OAUTH_TYPE = OKTA
    EXTERNAL_OAUTH_ISSUER = 'https://your-okta-domain.okta.com/oauth2/default'
    EXTERNAL_OAUTH_JWS_KEYS_URL = 'https://your-okta-domain.okta.com/oauth2/default/v1/keys'
    EXTERNAL_OAUTH_AUDIENCE_LIST = ('https://your-snowflake-account.snowflakecomputing.com')
    EXTERNAL_OAUTH_TOKEN_USER_MAPPING_CLAIM = 'sub'
    EXTERNAL_OAUTH_SNOWFLAKE_USER_MAPPING_ATTRIBUTE = 'EMAIL_ADDRESS'
    EXTERNAL_OAUTH_ANY_ROLE_MODE = 'ENABLE';
```

Replace:
- `your-okta-domain` with your Okta domain
- `your-snowflake-account` with your Snowflake account identifier

2. **Verify Integration**

```sql
DESC SECURITY INTEGRATION okta_oauth;
SHOW SECURITY INTEGRATIONS;
```

### Configure Okta Application

1. **Create New Application in Okta**
   - Go to Okta Admin Console
   - Applications → Create App Integration
   - Select "OIDC - OpenID Connect"
   - Select "Web Application"

2. **Configure Application Settings**
   ```
   Name: Snowflake Migration Agent
   Grant types: Authorization Code, Refresh Token
   Sign-in redirect URIs: https://your-app-domain/callback
   Sign-out redirect URIs: https://your-app-domain/logout
   Trusted Origins: https://your-snowflake-account.snowflakecomputing.com
   ```

3. **Note Credentials**
   - Client ID
   - Client Secret
   - Issuer URL

4. **Add Snowflake Scope**
   - Add custom scope: `session:role:MIGRATION_ROLE`
   - Add groups or users who can access

### Obtaining Access Token

**For Development/Testing:**

```bash
# Get access token using client credentials
curl --request POST \
  --url https://your-okta-domain.okta.com/oauth2/default/v1/token \
  --header 'content-type: application/x-www-form-urlencoded' \
  --data 'grant_type=client_credentials' \
  --data 'client_id=YOUR_CLIENT_ID' \
  --data 'client_secret=YOUR_CLIENT_SECRET' \
  --data 'scope=session:role:MIGRATION_ROLE'
```

**For Production:**

Implement proper OAuth flow in your application:
1. User authenticates with Okta
2. Okta redirects with authorization code
3. Exchange code for access token
4. Pass access token to migration agent

## PostgreSQL Configuration

### User Permissions

Create a dedicated migration user with read-only access:

```sql
-- Create user
CREATE USER migration_user WITH PASSWORD 'secure_password';

-- Grant CONNECT privilege
GRANT CONNECT ON DATABASE your_database TO migration_user;

-- Grant USAGE on schemas
GRANT USAGE ON SCHEMA public TO migration_user;
GRANT USAGE ON SCHEMA other_schema TO migration_user;

-- Grant SELECT on all tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO migration_user;
GRANT SELECT ON ALL TABLES IN SCHEMA other_schema TO migration_user;

-- Grant SELECT on future tables (optional)
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT ON TABLES TO migration_user;

-- Grant USAGE on sequences (for identity/serial columns)
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO migration_user;
```

### Network Access

**Allow connections from migration agent:**

Edit `pg_hba.conf`:
```
# Allow migration agent
host    your_database    migration_user    <agent_ip>/32    md5
```

Reload PostgreSQL configuration:
```bash
pg_ctl reload
# or
SELECT pg_reload_conf();
```

### SSL/TLS Configuration (Recommended)

**Enable SSL in PostgreSQL:**

In `postgresql.conf`:
```
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
ssl_ca_file = 'root.crt'
```

**In migration agent configuration:**
```python
ssl: {
    mode: "verify-full",
    ca: "/path/to/root.crt"
}
```

## Snowflake Configuration

### Create Migration Role

```sql
-- Create role
CREATE ROLE IF NOT EXISTS MIGRATION_ROLE;

-- Grant privileges
GRANT USAGE ON WAREHOUSE MIGRATION_WH TO ROLE MIGRATION_ROLE;
GRANT CREATE DATABASE ON ACCOUNT TO ROLE MIGRATION_ROLE;
GRANT CREATE SCHEMA ON DATABASE ECOMMERCE_PROD TO ROLE MIGRATION_ROLE;
GRANT CREATE TABLE ON SCHEMA ECOMMERCE_PROD.PUBLIC TO ROLE MIGRATION_ROLE;
GRANT CREATE STAGE ON SCHEMA ECOMMERCE_PROD.PUBLIC TO ROLE MIGRATION_ROLE;
GRANT CREATE FILE FORMAT ON SCHEMA ECOMMERCE_PROD.PUBLIC TO ROLE MIGRATION_ROLE;

-- Grant role to user (mapped from Okta)
GRANT ROLE MIGRATION_ROLE TO USER "user@example.com";
```

### Create Warehouse

```sql
CREATE WAREHOUSE IF NOT EXISTS MIGRATION_WH
    WAREHOUSE_SIZE = 'MEDIUM'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = FALSE;
```

**Recommended Sizes by Data Volume:**

| Data Size | Warehouse Size | Estimated Cost/Hour |
|-----------|---------------|---------------------|
| < 10 GB   | X-SMALL       | $2                  |
| 10-100 GB | SMALL-MEDIUM  | $4-8                |
| 100-500 GB| MEDIUM-LARGE  | $8-16               |
| > 500 GB  | LARGE-X-LARGE | $16-32              |

### Create Target Database

```sql
CREATE DATABASE IF NOT EXISTS ECOMMERCE_PROD;
USE DATABASE ECOMMERCE_PROD;

-- Create default schema
CREATE SCHEMA IF NOT EXISTS PUBLIC;

-- Create stage
CREATE STAGE IF NOT EXISTS MIGRATION_STAGE
    ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');

-- Create file format
CREATE FILE FORMAT IF NOT EXISTS MIGRATION_CSV_FORMAT
    TYPE = 'CSV'
    COMPRESSION = 'GZIP'
    FIELD_DELIMITER = ','
    RECORD_DELIMITER = '\n'
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    TRIM_SPACE = TRUE
    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE
    ESCAPE = 'NONE'
    ESCAPE_UNENCLOSED_FIELD = '\\'
    DATE_FORMAT = 'AUTO'
    TIMESTAMP_FORMAT = 'AUTO'
    NULL_IF = ('\\N', 'NULL', 'null', '');
```

### Network Policy (Optional)

Restrict access to specific IPs:

```sql
CREATE NETWORK POLICY migration_agent_policy
    ALLOWED_IP_LIST = ('<agent_ip>/32');

ALTER USER "user@example.com" 
SET NETWORK_POLICY = migration_agent_policy;
```

## Application Configuration

### Edit `.env` File

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# CORS Configuration (update with your frontend URL)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Logging
LOG_LEVEL=INFO

# File Storage (ensure these directories exist and are writable)
ARTIFACTS_PATH=./artifacts
TEMP_PATH=./temp

# Security (generate a strong random key)
SECRET_KEY=your-strong-random-secret-key-here

# Optional: Default values (can be overridden in UI)
# SNOWFLAKE_ACCOUNT=abc12345.us-east-1
# SNOWFLAKE_WAREHOUSE=MIGRATION_WH
# SNOWFLAKE_DATABASE=ECOMMERCE_PROD
```

### Generate Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Create Required Directories

```bash
mkdir -p artifacts
mkdir -p temp
mkdir -p logs
```

### Set Permissions

```bash
chmod 700 artifacts temp logs
```

## Verification

### Test Backend

```bash
# Start backend
cd backend
python -m uvicorn main:app --reload --port 8000

# In another terminal, test API
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00.000000"
}
```

### Test Frontend

```bash
# Start frontend dev server
cd frontend
npm run dev
```

Open browser to `http://localhost:3000`

### Test PostgreSQL Connection

```bash
# Using psql
psql -h localhost -U migration_user -d your_database

# Using Python
python -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='your_database',
    user='migration_user',
    password='your_password'
)
print('PostgreSQL connection successful')
conn.close()
"
```

### Test Snowflake Connection

```bash
# Using snowsql
snowsql -a abc12345.us-east-1 -u user@example.com --authenticator=externalbrowser

# Test OAuth token
curl --request POST \
  --url https://your-snowflake-account.snowflakecomputing.com/session/v1/login-request \
  --header 'Authorization: Bearer YOUR_OKTA_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{
    "data": {
      "ACCOUNT_NAME": "ABC12345",
      "LOGIN_NAME": "user@example.com"
    }
  }'
```

### Test Complete Flow

1. Open application in browser
2. Fill in test configuration
3. Click "Test Connections"
4. Start a dry run migration with small test database
5. Review generated artifacts
6. Verify all phases complete successfully

## Troubleshooting Setup

### Python Dependencies Fail

```bash
# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install build dependencies
# On Ubuntu/Debian:
sudo apt-get install python3-dev libpq-dev

# On macOS:
brew install postgresql

# On Windows:
# Download and install PostgreSQL binaries
```

### Node.js Dependencies Fail

```bash
# Clear npm cache
npm cache clean --force

# Remove node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Okta Token Issues

- Verify issuer URL is correct
- Check token hasn't expired (typically 1 hour)
- Ensure user has correct Snowflake role mapping
- Verify security integration in Snowflake

### Firewall/Network Issues

```bash
# Test PostgreSQL connectivity
nc -zv postgresql-host 5432
telnet postgresql-host 5432

# Test Snowflake connectivity
curl -v https://your-account.snowflakecomputing.com

# Test Okta connectivity
curl -v https://your-okta-domain.okta.com/.well-known/openid-configuration
```

### Permission Denied Errors

```bash
# Check directory permissions
ls -la artifacts temp logs

# Fix permissions
chmod -R 755 artifacts temp logs

# Check Python can write
python -c "
import os
os.makedirs('artifacts/test', exist_ok=True)
with open('artifacts/test/file.txt', 'w') as f:
    f.write('test')
print('Write test successful')
"
```

## Production Deployment

For production deployment, consider:

1. **Use production WSGI server**
   ```bash
   gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

2. **Build frontend for production**
   ```bash
   cd frontend
   npm run build
   # Serve build/ directory with nginx or similar
   ```

3. **Use environment variables**
   - Don't commit `.env` file
   - Use secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)

4. **Enable HTTPS**
   - Use SSL certificates
   - Configure reverse proxy (nginx, Apache)

5. **Set up monitoring**
   - Application logs
   - System metrics
   - Error tracking (Sentry, etc.)

6. **Database connection pooling**
   - Configure max connections
   - Use connection poolers if needed

7. **Backup strategy**
   - Regular backups of artifacts
   - Keep audit logs

---

**Setup complete!** Proceed to [User Guide](USER_GUIDE.md) for usage instructions.
