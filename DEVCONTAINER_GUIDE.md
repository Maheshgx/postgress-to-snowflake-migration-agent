# Dev Container and MCP Server Guide

Guide for running the PostgreSQL to Snowflake Migration Agent in a dev container and as an MCP server.

## Table of Contents

1. [Dev Container Setup](#dev-container-setup)
2. [MCP Server Setup](#mcp-server-setup)
3. [Docker Compose](#docker-compose)
4. [Usage Examples](#usage-examples)
5. [Troubleshooting](#troubleshooting)

---

## Dev Container Setup

### Prerequisites

- **Docker Desktop** (or Docker Engine + Docker Compose)
- **Visual Studio Code** with Dev Containers extension
- At least 4GB RAM available for Docker

### Quick Start

1. **Open in Dev Container**

   ```bash
   # Clone the repository
   git clone https://github.com/Maheshgx/postgress-to-snowflake-migration-agent.git
   cd postgress-to-snowflake-migration-agent
   
   # Open in VS Code
   code .
   ```

2. **Reopen in Container**
   - Press `F1` or `Cmd+Shift+P` (Mac) / `Ctrl+Shift+P` (Windows/Linux)
   - Select "Dev Containers: Reopen in Container"
   - Wait for container to build (first time takes 5-10 minutes)

3. **Automatic Setup**
   - Post-create script automatically runs
   - Python dependencies installed
   - Frontend dependencies installed
   - Required directories created

### What's Included

**Container Features:**
- Python 3.11 with all dependencies
- Node.js 18 for frontend
- PostgreSQL client tools
- Git and GitHub CLI
- VS Code extensions pre-installed

**Services:**
- **App Service** - Development environment
- **PostgreSQL** - Test database on port 5432

**Port Forwarding:**
- `8000` - Backend API
- `5173` - Frontend dev server
- `5432` - PostgreSQL test database

### Configuration Files

```
.devcontainer/
├── devcontainer.json       # Dev container configuration
├── Dockerfile             # Container image definition
└── post-create.sh         # Post-creation setup script
```

### Development Workflow

1. **Start Backend**
   ```bash
   cd backend
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start Frontend** (new terminal)
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access Application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

4. **Test PostgreSQL Connection**
   ```bash
   psql -h postgres -U postgres -d testdb
   # Password: postgres
   ```

### VS Code Extensions

Pre-installed extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Black Formatter (ms-python.black-formatter)
- Docker (ms-azuretools.vscode-docker)
- ESLint (dbaeumer.vscode-eslint)
- Prettier (esbenp.prettier-vscode)
- Tailwind CSS IntelliSense (bradlc.vscode-tailwindcss)

---

## MCP Server Setup

### What is MCP?

Model Context Protocol (MCP) enables AI assistants to interact with your migration agent through a standardized interface, providing:
- Tools for database analysis and migration
- Resources (documentation, templates)
- Prompts for common workflows

### Installation

1. **Install MCP Client**
   ```bash
   pip install mcp
   ```

2. **Configure MCP Server**
   
   The MCP configuration is in `mcp-server.json`:
   ```json
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

3. **Add to Your AI Assistant**

   For **Claude Desktop**, add to config file:
   
   **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   
   **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   
   ```json
   {
     "mcpServers": {
       "postgres-snowflake-migrator": {
         "command": "python",
         "args": [
           "/path/to/postgress-to-snowflake-migration-agent/backend/mcp_server.py"
         ],
         "env": {
           "PYTHONPATH": "/path/to/postgress-to-snowflake-migration-agent"
         }
       }
     }
   }
   ```

### Available Tools

The MCP server provides these tools:

1. **analyze_postgres_database**
   - Analyze PostgreSQL database schema
   - Returns: Complete analysis report

2. **start_migration**
   - Start database migration
   - Returns: Migration run_id and status

3. **check_migration_status**
   - Check migration progress
   - Returns: Current status and progress

4. **generate_snowflake_ddl**
   - Generate Snowflake DDL from analysis
   - Returns: DDL script

### Available Resources

1. **migration://docs/guide** - User guide
2. **migration://docs/architecture** - Architecture docs
3. **migration://config/template** - Configuration template

### Available Prompts

1. **analyze_database** - Database analysis workflow
2. **plan_migration** - Migration planning workflow

### Using MCP Server

**Example with AI Assistant:**

```
User: Analyze my PostgreSQL database at localhost/mydb

AI: I'll use the analyze_postgres_database tool to analyze your database.
    [Uses MCP tool with provided credentials]
    
    Analysis complete! Here's what I found:
    - 15 tables across 2 schemas
    - Total size: 2.3 GB
    - Compatibility issues: 3 JSON columns, 2 ARRAY columns
    
    Would you like me to generate the Snowflake DDL?
```

---

## Docker Compose

### Production Deployment

Use `docker-compose.yml` for production deployment:

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Services:**
- `backend` - FastAPI application on port 8000
- `frontend` - Nginx serving static files on port 3000
- `postgres` - Test PostgreSQL database on port 5432

### Development with Docker Compose

Use `docker-compose.dev.yml` for development:

```bash
# Start dev environment
docker-compose -f docker-compose.dev.yml up -d

# Enter app container
docker-compose -f docker-compose.dev.yml exec app bash

# Inside container
cd backend && python -m uvicorn main:app --reload --host 0.0.0.0
```

### Environment Variables

Configure via `.env` file or environment:

```bash
# API
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Storage
ARTIFACTS_PATH=/app/artifacts
TEMP_PATH=/app/temp

# Security
SECRET_KEY=your-secret-key-here
```

---

## Usage Examples

### Example 1: Dev Container Development

```bash
# 1. Open in dev container (VS Code)
# 2. Terminal 1: Start backend
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 3. Terminal 2: Start frontend
cd frontend
npm run dev

# 4. Access at http://localhost:5173
```

### Example 2: MCP Server with AI Assistant

```python
# AI Assistant can use these tools:

# Analyze database
{
  "tool": "analyze_postgres_database",
  "arguments": {
    "host": "localhost",
    "database": "mydb",
    "username": "user",
    "password": "pass"
  }
}

# Start migration
{
  "tool": "start_migration",
  "arguments": {
    "postgres": {...},
    "snowflake": {...},
    "auth": {"access_token": "..."},
    "dry_run": true
  }
}
```

### Example 3: Docker Production Deployment

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check health
curl http://localhost:8000/health

# View frontend
open http://localhost:3000
```

### Example 4: Test PostgreSQL Connection

```bash
# From dev container
psql -h postgres -U postgres -d testdb

# Run test migration
cd backend
python -c "
from postgres_analyzer import PostgresAnalyzer
from models import PostgresConfig

config = PostgresConfig(
    host='postgres',
    database='testdb',
    username='postgres',
    password='postgres'
)
analyzer = PostgresAnalyzer(config)
analyzer.connect()
result = analyzer.analyze()
print(result)
"
```

---

## Troubleshooting

### Dev Container Issues

**Container won't start:**
```bash
# Check Docker is running
docker ps

# Rebuild container
# In VS Code: Dev Containers: Rebuild Container

# Or manually
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d
```

**Permission denied:**
```bash
# Make post-create script executable
chmod +x .devcontainer/post-create.sh

# Fix directory permissions
chmod 755 artifacts temp logs
```

**Port already in use:**
```bash
# Find process using port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process or change port in devcontainer.json
```

### MCP Server Issues

**MCP server won't start:**
```bash
# Check Python path
which python

# Verify MCP installation
pip show mcp

# Test MCP server directly
python backend/mcp_server.py
```

**Tools not appearing:**
```bash
# Verify MCP config
cat mcp-server.json

# Check logs in AI assistant
# Claude Desktop logs: ~/Library/Logs/Claude/
```

### Docker Issues

**Build fails:**
```bash
# Clean Docker cache
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache
```

**Container crashes:**
```bash
# Check logs
docker-compose logs backend

# Check resource limits
docker stats

# Increase Docker memory limit (Docker Desktop settings)
```

**Database connection fails:**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U postgres -d testdb

# Check network
docker network inspect postgress-to-snowflake-migration-agent_migration-network
```

### Common Errors

**Import errors:**
```bash
# Update PYTHONPATH
export PYTHONPATH=/workspace:$PYTHONPATH

# Or in .env
PYTHONPATH=/workspace
```

**Frontend build fails:**
```bash
# Clear node_modules
rm -rf frontend/node_modules
cd frontend && npm install

# Clear npm cache
npm cache clean --force
```

**Missing dependencies:**
```bash
# Reinstall Python dependencies
pip install -r requirements.txt

# Reinstall with cache clear
pip install --no-cache-dir -r requirements.txt
```

---

## Best Practices

### Dev Container

1. **Commit .devcontainer/** - Share dev environment with team
2. **Update post-create.sh** - Add project-specific setup
3. **Use .env** - Never commit secrets
4. **Mount SSH keys** - For git operations

### MCP Server

1. **Secure credentials** - Use environment variables
2. **Test tools** - Verify each tool works
3. **Document prompts** - Help AI understand workflows
4. **Version control** - Track mcp-server.json changes

### Docker

1. **Multi-stage builds** - Smaller images
2. **Health checks** - Monitor service health
3. **Resource limits** - Prevent resource exhaustion
4. **Logging** - Centralized log management

---

## Production Deployment

After developing in the dev container, deploy to production:

**For Company Intranet:**
- See [INTRANET_DEPLOYMENT.md](INTRANET_DEPLOYMENT.md)
- Single server, load balanced, or Kubernetes
- Complete security hardening
- Monitoring and alerting

**For AI Assistant Integration:**
- See [MCP_DEPLOYMENT.md](MCP_DEPLOYMENT.md)
- Claude Desktop configuration
- Server deployment options
- Natural language interface

---

## Additional Resources

- **Dev Containers**: https://code.visualstudio.com/docs/devcontainers/containers
- **MCP Protocol**: https://modelcontextprotocol.io
- **Docker Compose**: https://docs.docker.com/compose/
- **Getting Started**: [GETTING_STARTED.md](GETTING_STARTED.md)
- **Intranet Deployment**: [INTRANET_DEPLOYMENT.md](INTRANET_DEPLOYMENT.md)
- **MCP Deployment**: [MCP_DEPLOYMENT.md](MCP_DEPLOYMENT.md)
- **Developer Guide**: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Project Docs**: See [README.md](README.md)

---

**Happy containerized development!** 🐳
