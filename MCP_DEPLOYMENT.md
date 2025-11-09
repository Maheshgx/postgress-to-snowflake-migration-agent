# MCP Extension Deployment Guide

Complete guide for deploying the PostgreSQL to Snowflake Migration Agent as a Model Context Protocol (MCP) server for AI assistants.

## Table of Contents

1. [What is MCP?](#what-is-mcp)
2. [MCP Server Overview](#mcp-server-overview)
3. [Local Development Setup](#local-development-setup)
4. [Claude Desktop Integration](#claude-desktop-integration)
5. [Server Deployment](#server-deployment)
6. [Testing MCP Tools](#testing-mcp-tools)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)

---

## What is MCP?

### Model Context Protocol Overview

MCP (Model Context Protocol) is a standardized protocol that enables AI assistants to:
- **Access external tools** - Execute functions in your applications
- **Read resources** - Access documentation, templates, and data
- **Use prompts** - Leverage pre-defined workflows

### Benefits

✅ **For Users:**
- Natural language interface to migration tools
- AI-assisted database analysis and migration
- Automated workflow execution

✅ **For Organizations:**
- Consistent migration processes
- Reduced manual errors
- Knowledge capture in prompts

✅ **For Developers:**
- Standardized integration
- Easy to extend with new tools
- Works with multiple AI assistants

### Architecture

```
┌─────────────────────────────────────────────┐
│          AI Assistant (Claude)              │
│                                             │
│  "Analyze my PostgreSQL database"          │
└──────────────────┬──────────────────────────┘
                   │ MCP Protocol
                   │ (JSON-RPC over stdio)
                   │
┌──────────────────▼──────────────────────────┐
│          MCP Server                         │
│     (backend/mcp_server.py)                 │
│                                             │
│  Tools:                                     │
│  - analyze_postgres_database                │
│  - start_migration                          │
│  - check_migration_status                   │
│  - generate_snowflake_ddl                   │
│                                             │
│  Resources:                                 │
│  - Documentation                            │
│  - Configuration templates                  │
│                                             │
│  Prompts:                                   │
│  - Database analysis workflow               │
│  - Migration planning workflow              │
└──────────────────┬──────────────────────────┘
                   │
                   │ Direct API calls
                   │
┌──────────────────▼──────────────────────────┐
│      Migration Agent Backend                │
│         (FastAPI Application)               │
└─────────────────────────────────────────────┘
```

---

## MCP Server Overview

### Available Tools

The MCP server exposes these tools to AI assistants:

#### 1. `analyze_postgres_database`
**Description:** Analyze PostgreSQL database schema and structure

**Input:**
```json
{
  "postgres_config": {
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "username": "user",
    "password": "pass",
    "schemas": ["public"]
  }
}
```

**Output:**
- Complete schema analysis
- Table statistics
- Data type inventory
- Compatibility assessment

#### 2. `start_migration`
**Description:** Start a database migration (dry run or full)

**Input:**
```json
{
  "postgres_config": {...},
  "snowflake_config": {...},
  "oauth_config": {"access_token": "..."},
  "preferences": {
    "dry_run": true,
    "format": "csv",
    "parallelism": 4
  }
}
```

**Output:**
- Migration run ID
- Status
- Progress updates

#### 3. `check_migration_status`
**Description:** Check status of running migration

**Input:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Output:**
- Current phase
- Progress percentage
- Table statuses
- Errors (if any)

#### 4. `generate_snowflake_ddl`
**Description:** Generate Snowflake DDL from PostgreSQL analysis

**Input:**
```json
{
  "analysis_report": {...},
  "preferences": {
    "case_style": "UPPER",
    "use_identity": true
  }
}
```

**Output:**
- Complete DDL script
- Type mappings
- Recommendations

### Available Resources

#### 1. `migration://docs/guide`
Complete user guide documentation

#### 2. `migration://docs/architecture`
System architecture documentation

#### 3. `migration://config/template`
Configuration template with examples

### Available Prompts

#### 1. `analyze_database`
**Description:** Guide user through database analysis
**Arguments:** PostgreSQL connection details

#### 2. `plan_migration`
**Description:** Help plan migration strategy
**Arguments:** Database name, size, complexity

---

## Local Development Setup

### Step 1: Install MCP Python SDK

```bash
# Activate your virtual environment
source venv/bin/activate

# Install MCP SDK (already in requirements.txt)
pip install mcp==0.9.0

# Verify installation
python -c "import mcp; print(mcp.__version__)"
```

### Step 2: Test MCP Server

```bash
# Navigate to project root
cd /path/to/postgress-to-snowflake-migration-agent

# Set PYTHONPATH
export PYTHONPATH=$PWD

# Test MCP server directly
python backend/mcp_server.py

# You should see:
# MCP server starting...
# Available tools: analyze_postgres_database, start_migration, ...
```

### Step 3: Verify MCP Configuration

```bash
# Check mcp-server.json
cat mcp-server.json

# Should contain:
{
  "mcpServers": {
    "postgres-snowflake-migrator": {
      "command": "python",
      "args": ["-m", "backend.mcp_server"],
      "env": {
        "API_HOST": "0.0.0.0",
        "API_PORT": "8000"
      }
    }
  }
}
```

---

## Claude Desktop Integration

### For macOS

#### Step 1: Locate Claude Config

```bash
# Claude Desktop config location
CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

# Create directory if it doesn't exist
mkdir -p "$HOME/Library/Application Support/Claude"
```

#### Step 2: Add MCP Server Configuration

```bash
# Get absolute path to your project
PROJECT_PATH="/path/to/postgress-to-snowflake-migration-agent"

# Create or edit config file
cat > "$CONFIG_FILE" << EOF
{
  "mcpServers": {
    "postgres-snowflake-migrator": {
      "command": "python",
      "args": [
        "${PROJECT_PATH}/backend/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "${PROJECT_PATH}",
        "API_HOST": "localhost",
        "API_PORT": "8000"
      }
    }
  }
}
EOF
```

#### Step 3: Restart Claude Desktop

```bash
# Quit Claude Desktop completely
# Reopen Claude Desktop

# Check logs for MCP server startup
tail -f "$HOME/Library/Logs/Claude/mcp*.log"
```

### For Windows

#### Step 1: Locate Claude Config

```powershell
# Config location
$ConfigFile = "$env:APPDATA\Claude\claude_desktop_config.json"

# Create directory
New-Item -Path "$env:APPDATA\Claude" -ItemType Directory -Force
```

#### Step 2: Add Configuration

```powershell
# Set your project path
$ProjectPath = "C:\Users\YourName\postgress-to-snowflake-migration-agent"

# Create config
@"
{
  "mcpServers": {
    "postgres-snowflake-migrator": {
      "command": "python",
      "args": [
        "$ProjectPath\\backend\\mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "$ProjectPath"
      }
    }
  }
}
"@ | Out-File -FilePath $ConfigFile -Encoding UTF8
```

#### Step 3: Restart Claude Desktop

Completely quit and reopen Claude Desktop.

### For Linux

```bash
# Config location
CONFIG_FILE="$HOME/.config/Claude/claude_desktop_config.json"
mkdir -p "$HOME/.config/Claude"

# Add configuration (same as macOS)
PROJECT_PATH="/home/yourusername/postgress-to-snowflake-migration-agent"

cat > "$CONFIG_FILE" << EOF
{
  "mcpServers": {
    "postgres-snowflake-migrator": {
      "command": "python",
      "args": ["${PROJECT_PATH}/backend/mcp_server.py"],
      "env": {
        "PYTHONPATH": "${PROJECT_PATH}"
      }
    }
  }
}
EOF
```

---

## Server Deployment

### Option 1: Deploy on Dedicated MCP Server

For organization-wide MCP server accessible to all AI assistants.

#### Step 1: Set Up Server

```bash
# SSH to server
ssh admin@mcp-server.company.local

# Create MCP user
sudo useradd -m -s /bin/bash mcpuser
sudo su - mcpuser

# Clone repository
git clone https://github.company.local/.../migration-agent.git
cd migration-agent

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Step 2: Configure MCP Service

```bash
# Create systemd service
sudo tee /etc/systemd/system/mcp-migration-agent.service << 'EOF'
[Unit]
Description=MCP Server - PostgreSQL to Snowflake Migration Agent
After=network.target

[Service]
Type=simple
User=mcpuser
Group=mcpuser
WorkingDirectory=/home/mcpuser/migration-agent
Environment="PYTHONPATH=/home/mcpuser/migration-agent"
Environment="API_HOST=localhost"
Environment="API_PORT=8000"
ExecStart=/home/mcpuser/migration-agent/venv/bin/python backend/mcp_server.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mcp-migration-agent

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable mcp-migration-agent
sudo systemctl start mcp-migration-agent

# Check status
sudo systemctl status mcp-migration-agent
```

#### Step 3: Configure Networking

```bash
# MCP over HTTP (for remote AI assistants)
# Install MCP HTTP wrapper
pip install mcp-http-server

# Create HTTP wrapper service
cat > /home/mcpuser/mcp-http-wrapper.py << 'EOF'
from mcp_http_server import serve
import sys
sys.path.insert(0, '/home/mcpuser/migration-agent')
from backend.mcp_server import create_server

if __name__ == "__main__":
    server = create_server()
    serve(server, host="0.0.0.0", port=8100)
EOF

# Create systemd service for HTTP wrapper
sudo tee /etc/systemd/system/mcp-http-migration-agent.service << 'EOF'
[Unit]
Description=MCP HTTP Server - Migration Agent
After=network.target

[Service]
Type=simple
User=mcpuser
WorkingDirectory=/home/mcpuser/migration-agent
ExecStart=/home/mcpuser/migration-agent/venv/bin/python /home/mcpuser/mcp-http-wrapper.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable mcp-http-migration-agent
sudo systemctl start mcp-http-migration-agent
```

#### Step 4: Configure Reverse Proxy

```bash
# Nginx configuration for MCP HTTP endpoint
sudo tee /etc/nginx/sites-available/mcp-migration-agent << 'EOF'
server {
    listen 443 ssl http2;
    server_name mcp.company.local;

    ssl_certificate /etc/ssl/certs/mcp.crt;
    ssl_certificate_key /etc/ssl/private/mcp.key;

    location / {
        proxy_pass http://127.0.0.1:8100;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Authentication
        auth_basic "MCP Access";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/mcp-migration-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Option 2: Docker Deployment

```bash
# Create Dockerfile.mcp
cat > Dockerfile.mcp << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ ./backend/
COPY .env.example .env

# Set environment
ENV PYTHONPATH=/app
ENV API_HOST=localhost
ENV API_PORT=8000

# Run MCP server
CMD ["python", "backend/mcp_server.py"]
EOF

# Build image
docker build -f Dockerfile.mcp -t migration-agent-mcp:latest .

# Run container
docker run -d \
  --name migration-agent-mcp \
  --restart unless-stopped \
  -e PYTHONPATH=/app \
  -e API_HOST=migration-backend \
  -e API_PORT=8000 \
  --network migration-network \
  migration-agent-mcp:latest

# Check logs
docker logs -f migration-agent-mcp
```

### Option 3: Kubernetes Deployment

```yaml
# mcp-deployment.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-config
data:
  API_HOST: "migration-backend-service"
  API_PORT: "8000"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-migration-agent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mcp-migration-agent
  template:
    metadata:
      labels:
        app: mcp-migration-agent
    spec:
      containers:
      - name: mcp-server
        image: migration-agent-mcp:latest
        envFrom:
        - configMapRef:
            name: mcp-config
        ports:
        - containerPort: 8100
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: mcp-service
spec:
  selector:
    app: mcp-migration-agent
  ports:
  - port: 8100
    targetPort: 8100
  type: ClusterIP
```

Deploy:
```bash
kubectl apply -f mcp-deployment.yaml
kubectl get pods -l app=mcp-migration-agent
```

---

## Testing MCP Tools

### Test in Claude Desktop

After configuring Claude Desktop:

**Example 1: Database Analysis**
```
You: I need to analyze my PostgreSQL database at localhost, database name "customers_db", user "postgres", password "mypass123"

Claude: I'll use the analyze_postgres_database tool to analyze your database.

[Claude uses the MCP tool]

Claude: Analysis complete! Your database has:
- 12 tables across 2 schemas
- Total size: 4.2 GB
- 3 compatibility issues found:
  1. JSON columns in logs table
  2. Array type in products.tags
  3. Enum type in orders.status

Would you like me to generate the Snowflake DDL?
```

**Example 2: Generate DDL**
```
You: Yes, generate the DDL

Claude: [Uses generate_snowflake_ddl tool]

I've generated the complete Snowflake DDL. Here are the key mappings:
- JSON → VARIANT
- Arrays → VARIANT
- Enums → VARCHAR with CHECK constraint comments

The DDL has been created. Should I start a dry run migration?
```

**Example 3: Start Migration**
```
You: Start a dry run migration

Claude: [Uses start_migration tool with dry_run: true]

Dry run migration started!
Run ID: 550e8400-e29b-41d4-a716-446655440000

Current status:
- Phase: ANALYZING
- Progress: 25%
- Tables analyzed: 3/12

I'll check the status in a moment...
```

### Test via CLI

```bash
# Install MCP CLI
pip install mcp-cli

# List available servers
mcp servers list

# List tools from server
mcp tools list postgres-snowflake-migrator

# Call a tool
mcp tools call postgres-snowflake-migrator analyze_postgres_database \
  --postgres_config '{"host":"localhost","database":"testdb",...}'

# Read a resource
mcp resources read postgres-snowflake-migrator migration://docs/guide
```

### Test with Python Client

```python
from mcp.client import Client
import asyncio

async def test_mcp_tool():
    # Connect to MCP server
    async with Client("postgres-snowflake-migrator") as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {[t.name for t in tools]}")
        
        # Call analyze tool
        result = await client.call_tool(
            "analyze_postgres_database",
            postgres_config={
                "host": "localhost",
                "port": 5432,
                "database": "testdb",
                "username": "user",
                "password": "pass",
                "schemas": ["public"]
            }
        )
        
        print(f"Analysis result: {result}")

# Run test
asyncio.run(test_mcp_tool())
```

---

## Advanced Configuration

### Environment Variables

```bash
# .env.mcp
PYTHONPATH=/path/to/project
API_HOST=localhost
API_PORT=8000

# Backend API credentials (if needed)
API_KEY=your-api-key

# Logging
LOG_LEVEL=INFO
MCP_LOG_FILE=/var/log/mcp-migration-agent.log

# Timeouts
MCP_TIMEOUT=300
REQUEST_TIMEOUT=60
```

### Custom Tool Addition

Add new tool to `backend/mcp_server.py`:

```python
@server.tool()
async def estimate_migration_cost(
    analysis_report: dict,
    snowflake_warehouse_size: str = "MEDIUM"
) -> dict:
    """
    Estimate Snowflake compute cost for migration.
    
    Args:
        analysis_report: Database analysis report
        snowflake_warehouse_size: Warehouse size (XSMALL to XXLARGE)
    
    Returns:
        Cost estimation breakdown
    """
    # Calculate based on data volume and warehouse size
    total_gb = sum(t.get("size_bytes", 0) for t in analysis_report.get("tables", [])) / (1024**3)
    
    # Warehouse costs per hour (example rates)
    warehouse_costs = {
        "XSMALL": 1,
        "SMALL": 2,
        "MEDIUM": 4,
        "LARGE": 8,
        "XLARGE": 16
    }
    
    # Estimate duration (GB per hour depends on warehouse size)
    throughput = {
        "XSMALL": 10,
        "SMALL": 20,
        "MEDIUM": 40,
        "LARGE": 80,
        "XLARGE": 160
    }
    
    cost_per_hour = warehouse_costs.get(snowflake_warehouse_size, 4)
    gb_per_hour = throughput.get(snowflake_warehouse_size, 40)
    estimated_hours = total_gb / gb_per_hour
    estimated_cost = estimated_hours * cost_per_hour
    
    return {
        "total_gb": round(total_gb, 2),
        "warehouse_size": snowflake_warehouse_size,
        "estimated_hours": round(estimated_hours, 2),
        "estimated_cost_usd": round(estimated_cost, 2),
        "cost_per_hour": cost_per_hour
    }
```

### Authentication & Authorization

Add authentication to MCP server:

```python
# backend/mcp_auth.py
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key"

def create_mcp_token(user: str, permissions: list) -> str:
    """Create JWT token for MCP access"""
    payload = {
        "user": user,
        "permissions": permissions,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_mcp_token(token: str) -> dict:
    """Verify JWT token"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

# Add to server
@server.middleware
async def auth_middleware(request, handler):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise ValueError("No authorization token")
    
    user_info = verify_mcp_token(token)
    request.user = user_info
    return await handler(request)
```

---

## Troubleshooting

### MCP Server Not Starting

**Problem:** Server fails to start in Claude Desktop

**Solution:**
```bash
# Check Python path
which python

# Test server directly
cd /path/to/project
export PYTHONPATH=$PWD
python backend/mcp_server.py

# Check logs
tail -f "$HOME/Library/Logs/Claude/mcp*.log"  # macOS
tail -f "$HOME/.config/Claude/logs/mcp*.log"  # Linux
```

### Tools Not Appearing

**Problem:** Tools don't show up in Claude

**Solution:**
```bash
# Verify config file
cat "$HOME/Library/Application Support/Claude/claude_desktop_config.json"

# Check JSON syntax
python -m json.tool < claude_desktop_config.json

# Restart Claude completely
pkill -9 Claude
open -a Claude

# Wait 30 seconds for MCP server to initialize
```

### Permission Denied

**Problem:** `PermissionError: [Errno 13]`

**Solution:**
```bash
# Make MCP server executable
chmod +x backend/mcp_server.py

# Check file ownership
ls -la backend/mcp_server.py

# Fix if needed
chown $USER backend/mcp_server.py
```

### Module Not Found

**Problem:** `ModuleNotFoundError: No module named 'backend'`

**Solution:**
```bash
# Ensure PYTHONPATH is set correctly in config
{
  "mcpServers": {
    "postgres-snowflake-migrator": {
      "env": {
        "PYTHONPATH": "/absolute/path/to/project"
      }
    }
  }
}

# Or use python -m
"args": ["python", "-m", "backend.mcp_server"]
```

### Connection Timeout

**Problem:** MCP calls timeout

**Solution:**
```python
# Increase timeout in mcp_server.py
server = Server(
    name="postgres-snowflake-migrator",
    version="1.0.0",
    timeout=300  # 5 minutes
)
```

### Backend API Not Accessible

**Problem:** MCP server can't reach backend API

**Solution:**
```bash
# Check backend is running
curl http://localhost:8000/health

# Start backend if needed
cd backend
python -m uvicorn main:app --reload

# Or start in background
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
```

---

## Production Checklist

Before deploying MCP server to production:

- [ ] Backend API is running and accessible
- [ ] MCP server configuration tested locally
- [ ] Authentication/authorization implemented
- [ ] Rate limiting configured
- [ ] Logging configured
- [ ] Monitoring alerts set up
- [ ] Error handling tested
- [ ] Documentation updated
- [ ] User training completed
- [ ] Backup procedures in place

---

## Additional Resources

- **MCP Specification:** https://modelcontextprotocol.io/docs/specification
- **MCP Python SDK:** https://github.com/modelcontextprotocol/python-sdk
- **Claude MCP Integration:** https://docs.anthropic.com/claude/docs/mcp
- **Project Documentation:** See [README.md](README.md), [GETTING_STARTED.md](GETTING_STARTED.md)

---

**Your migration agent is now available as an MCP extension!** AI assistants can analyze databases, generate DDL, and manage migrations through natural language. 🎉
