# PostgreSQL → Snowflake Migration Agent

**Web-hosted, auditable database migration tool with Okta SSO integration**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18.2-blue.svg)](https://reactjs.org/)

## 🎯 Overview

A production-grade migration agent that analyzes PostgreSQL databases, proposes optimized Snowflake schemas, and executes end-to-end migrations with comprehensive validation and auditability. Designed for enterprise use with Okta External OAuth authentication.

### Key Features

- **🔍 Comprehensive Analysis** - Deep introspection of PostgreSQL schemas, tables, constraints, indexes, and special types
- **🎨 Intelligent Mapping** - Smart type conversion with JSON→VARIANT, proper identity/sequence handling
- **🔒 Secure** - Okta External OAuth for Snowflake, credential redaction in logs
- **📊 Progress Tracking** - Real-time migration progress with table-level status
- **✅ Validation** - Automated data quality checks, row count verification, constraint validation
- **📝 Audit Trail** - Complete paper trail with structured logging (NDJSON)
- **🎭 Dry Run Mode** - Analyze and plan without executing
- **⚡ Parallel Execution** - Configurable parallelism for faster migrations
- **🌐 Modern UI** - React + TailwindCSS interface for easy configuration and monitoring

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Setup Instructions](#-setup-instructions)
- [Usage](#-usage)
- [Documentation](#-documentation)
- [Contributing](#-contributing)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL database (source)
- Snowflake account with Okta External OAuth configured
- Active Okta OAuth access token

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd postgress-to-snowflake-migration-agent

# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..

# Configure environment
cp .env.example .env
# Edit .env with your configuration
```

### Running the Application

**Option 1: Local Development**
```bash
# Terminal 1: Start backend API
cd backend
python -m uvicorn main:app --reload --port 8000

# Terminal 2: Start frontend dev server
cd frontend
npm run dev
```

**Option 2: Dev Container (Recommended)**
```bash
# Open in VS Code and reopen in container
# Or use CLI:
devcontainer open .
```

**Option 3: Docker Compose**
```bash
# Production deployment
docker-compose up -d

# Development mode
docker-compose -f docker-compose.dev.yml up -d
```

Access the application at `http://localhost:5173` (dev) or `http://localhost:3000` (production)

## 🏗️ Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   PostgreSQL    │─────▶│  Migration Agent │─────▶│   Snowflake     │
│    (Source)     │      │   (Web App)      │      │   (Target)      │
└─────────────────┘      └──────────────────┘      └─────────────────┘
                               │
                               │ Okta OAuth
                               ▼
                         ┌──────────────┐
                         │  Okta SSO    │
                         └──────────────┘
```

### Components

- **Backend (FastAPI)** - REST API, migration orchestration, database connections
- **Frontend (React)** - Modern UI for configuration, monitoring, and artifacts
- **Analyzer** - PostgreSQL introspection and analysis
- **Generator** - Snowflake DDL and migration plan generation
- **Pipeline** - Data extraction, transformation, and loading
- **Validator** - Post-migration data validation

## 🛠️ Setup Instructions

See [SETUP.md](SETUP.md) for detailed setup instructions including:
- Okta External OAuth configuration
- PostgreSQL permissions
- Snowflake warehouse setup
- Network and firewall requirements

## 📖 Usage

### 1. Configure Source and Target

Fill in the web form with:
- **PostgreSQL**: Host, port, database, credentials, schemas
- **Snowflake**: Account, warehouse, database, role, stage, file format
- **OAuth**: Your Okta access token
- **Preferences**: Data format (CSV/Parquet), parallelism, case style

### 2. Test Connections

Click "Test Connections" to verify connectivity before starting.

### 3. Start Migration

**Dry Run (Recommended First)**
- Check "Dry Run" option
- Reviews analysis and plan without executing
- Generates all artifacts for review

**Full Migration**
- Uncheck "Dry Run"
- Click "Start Migration"
- Monitor real-time progress
- Review validation results

### 4. Review Artifacts

Download and review generated artifacts:
- `analysis_report.json` - Complete PostgreSQL analysis
- `snowflake_objects.sql` - DDL for Snowflake objects
- `mapping_decisions.yml` - Type mapping rationale
- `improvement_recommendations.md` - Optimization tips
- `post_migration_checks.sql` - Validation queries
- `summary.md` - Migration report with next steps

## 📚 Documentation

- **[🚀 Getting Started Guide](GETTING_STARTED.md)** - **START HERE!** Complete walkthrough from setup to first migration
- **[User Guide](USER_GUIDE.md)** - Detailed usage instructions and workflows
- **[Developer Guide](DEVELOPER_GUIDE.md)** - Code walkthrough and extension points
- **[Setup Instructions](SETUP.md)** - Advanced installation and configuration
- **[Intranet Deployment](INTRANET_DEPLOYMENT.md)** - Deploy on company intranet infrastructure
- **[MCP Deployment](MCP_DEPLOYMENT.md)** - Deploy as AI assistant extension (Claude, etc.)
- **[Dev Container Guide](DEVCONTAINER_GUIDE.md)** - Dev container and development environment
- **[Architecture](ARCHITECTURE.md)** - System design and components
- **[Requirements](REQUIREMENTS.md)** - System and application requirements
- **[Project Creation Prompt](PROJECT_CREATION_PROMPT.md)** - Master prompt that created this project

## 🔑 Key Features in Detail

### Intelligent Type Mapping

- **JSON/JSONB** → `VARIANT` with projection view recommendations
- **BYTEA** → `BINARY`
- **UUID** → `VARCHAR(36)` (or `BINARY(16)`)
- **Arrays** → `VARIANT`
- **Enums** → `VARCHAR` with validation notes
- **Serial/Identity** → `IDENTITY` or `SEQUENCE`

### Constraint Handling

- **Primary Keys** - Created as metadata (not enforced on standard tables)
- **Unique Keys** - Created as metadata
- **Foreign Keys** - Documented in comments
- **NOT NULL** - Enforced
- **CHECK** - Documented; requires manual implementation

### Data Quality Validation

- Row count verification
- NOT NULL constraint checks
- Primary key duplicate detection
- JSON validity verification
- Timestamp sanity checks

### Security & Compliance

- OAuth-based Snowflake authentication
- Credential redaction in logs
- Audit trail (NDJSON format)
- No passwords in configuration files
- Role-based access control templates

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues, questions, or feature requests, please open an issue on GitHub.

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Backend API framework
- [React](https://reactjs.org/) - Frontend framework
- [TailwindCSS](https://tailwindcss.com/) - UI styling
- [Snowflake Connector](https://docs.snowflake.com/en/user-guide/python-connector.html) - Snowflake Python SDK
- [psycopg2](https://www.psycopg.org/) - PostgreSQL adapter

---

**⚠️ Important**: Always test migrations in a development environment before production. Review all generated DDL and validation results carefully.
