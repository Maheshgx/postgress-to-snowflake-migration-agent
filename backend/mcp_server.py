"""
MCP (Model Context Protocol) Server implementation for the migration agent.

This allows the migration agent to be used as an MCP server, providing
tools, prompts, and resources for AI assistants.
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, Resource, Prompt, TextContent

from backend.main import app
from backend.models import MigrationRequest, MigrationStatus
from backend.migrator import MigrationOrchestrator
from backend.postgres_analyzer import PostgresAnalyzer
from backend.config import settings


# Initialize MCP server
mcp_server = Server("postgres-snowflake-migrator")


@mcp_server.list_tools()
async def list_tools() -> List[Tool]:
    """
    List available migration tools.
    """
    return [
        Tool(
            name="analyze_postgres_database",
            description="Analyze a PostgreSQL database schema and structure",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "PostgreSQL host"},
                    "port": {"type": "integer", "description": "PostgreSQL port", "default": 5432},
                    "database": {"type": "string", "description": "Database name"},
                    "username": {"type": "string", "description": "Database username"},
                    "password": {"type": "string", "description": "Database password"},
                    "schemas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Schemas to analyze (or ['*'] for all)",
                        "default": ["*"]
                    }
                },
                "required": ["host", "database", "username", "password"]
            }
        ),
        Tool(
            name="start_migration",
            description="Start a database migration from PostgreSQL to Snowflake",
            inputSchema={
                "type": "object",
                "properties": {
                    "postgres": {
                        "type": "object",
                        "description": "PostgreSQL connection configuration"
                    },
                    "snowflake": {
                        "type": "object",
                        "description": "Snowflake connection configuration"
                    },
                    "auth": {
                        "type": "object",
                        "description": "OAuth authentication configuration"
                    },
                    "preferences": {
                        "type": "object",
                        "description": "Migration preferences"
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Perform dry run (analysis only)",
                        "default": true
                    }
                },
                "required": ["postgres", "snowflake", "auth"]
            }
        ),
        Tool(
            name="check_migration_status",
            description="Check the status of a running migration",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "Migration run ID"
                    }
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="generate_snowflake_ddl",
            description="Generate Snowflake DDL from PostgreSQL analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "analysis_data": {
                        "type": "object",
                        "description": "PostgreSQL analysis data"
                    },
                    "preferences": {
                        "type": "object",
                        "description": "DDL generation preferences"
                    }
                },
                "required": ["analysis_data"]
            }
        )
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Handle tool execution.
    """
    if name == "analyze_postgres_database":
        from backend.postgres_analyzer import PostgresAnalyzer
        from backend.models import PostgresConfig
        
        # Create config from arguments
        config = PostgresConfig(**arguments)
        
        # Run analysis
        analyzer = PostgresAnalyzer(config)
        try:
            analyzer.connect()
            analysis = analyzer.analyze()
            analyzer.disconnect()
            
            return [TextContent(
                type="text",
                text=json.dumps(analysis, indent=2, default=str)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error analyzing database: {str(e)}"
            )]
    
    elif name == "start_migration":
        import uuid
        from backend.models import MigrationRequest
        
        # Parse request
        request = MigrationRequest(**arguments)
        run_id = str(uuid.uuid4())
        
        # Create orchestrator
        orchestrator = MigrationOrchestrator(run_id, request)
        
        # Start migration (async)
        asyncio.create_task(orchestrator.run())
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "run_id": run_id,
                "status": "started",
                "message": "Migration started in background"
            })
        )]
    
    elif name == "check_migration_status":
        run_id = arguments["run_id"]
        
        # Get status from global migrations dict
        from backend.main import migrations
        
        if run_id in migrations:
            status = migrations[run_id]
            return [TextContent(
                type="text",
                text=json.dumps(status.dict(), indent=2, default=str)
            )]
        else:
            return [TextContent(
                type="text",
                text=f"Migration {run_id} not found"
            )]
    
    elif name == "generate_snowflake_ddl":
        from backend.snowflake_generator import SnowflakeGenerator
        from backend.models import MigrationPreferences
        
        analysis = arguments["analysis_data"]
        preferences = MigrationPreferences(**arguments.get("preferences", {}))
        
        generator = SnowflakeGenerator(analysis, preferences)
        ddl = generator.generate_ddl()
        
        return [TextContent(
            type="text",
            text=ddl
        )]
    
    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]


@mcp_server.list_resources()
async def list_resources() -> List[Resource]:
    """
    List available resources.
    """
    return [
        Resource(
            uri="migration://docs/guide",
            name="Migration Guide",
            mimeType="text/markdown",
            description="Complete guide for database migration"
        ),
        Resource(
            uri="migration://docs/architecture",
            name="Architecture Documentation",
            mimeType="text/markdown",
            description="System architecture and design"
        ),
        Resource(
            uri="migration://config/template",
            name="Configuration Template",
            mimeType="application/json",
            description="Migration configuration template"
        )
    ]


@mcp_server.read_resource()
async def read_resource(uri: str) -> str:
    """
    Read resource content.
    """
    if uri == "migration://docs/guide":
        try:
            with open("USER_GUIDE.md", "r") as f:
                return f.read()
        except FileNotFoundError:
            return "User guide not found"
    
    elif uri == "migration://docs/architecture":
        try:
            with open("ARCHITECTURE.md", "r") as f:
                return f.read()
        except FileNotFoundError:
            return "Architecture documentation not found"
    
    elif uri == "migration://config/template":
        template = {
            "postgres": {
                "host": "localhost",
                "port": 5432,
                "database": "mydb",
                "username": "user",
                "password": "password",
                "schemas": ["*"]
            },
            "snowflake": {
                "account": "abc12345.us-east-1",
                "warehouse": "MIGRATION_WH",
                "database": "TARGET_DB",
                "default_role": "MIGRATION_ROLE",
                "schema": "PUBLIC",
                "stage": "MIGRATION_STAGE",
                "file_format": "MIGRATION_CSV_FORMAT"
            },
            "auth": {
                "access_token": "your-okta-token"
            },
            "preferences": {
                "format": "CSV",
                "max_chunk_mb": 200,
                "parallelism": 4,
                "use_identity_for_serial": True,
                "case_style": "UPPER",
                "dry_run": True
            }
        }
        return json.dumps(template, indent=2)
    
    else:
        return f"Resource not found: {uri}"


@mcp_server.list_prompts()
async def list_prompts() -> List[Prompt]:
    """
    List available prompts.
    """
    return [
        Prompt(
            name="analyze_database",
            description="Analyze a PostgreSQL database for migration",
            arguments=[
                {"name": "host", "description": "Database host", "required": True},
                {"name": "database", "description": "Database name", "required": True}
            ]
        ),
        Prompt(
            name="plan_migration",
            description="Create a migration plan from analysis",
            arguments=[
                {"name": "analysis", "description": "Analysis data", "required": True}
            ]
        )
    ]


@mcp_server.get_prompt()
async def get_prompt(name: str, arguments: Optional[Dict[str, str]]) -> str:
    """
    Get prompt content.
    """
    if name == "analyze_database":
        host = arguments.get("host", "localhost")
        database = arguments.get("database", "mydb")
        return f"""
Analyze the PostgreSQL database at {host}/{database} for migration to Snowflake.

Please provide:
1. Connection credentials (username, password)
2. Schemas to analyze (or * for all)
3. Any specific tables to focus on

The analysis will examine:
- Database schema structure
- Table definitions and relationships
- Data types and constraints
- Volumetrics and sizing
- Compatibility issues
"""
    
    elif name == "plan_migration":
        return """
Based on the PostgreSQL analysis, create a comprehensive migration plan:

1. Review the analysis results
2. Identify any compatibility issues
3. Generate Snowflake DDL
4. Plan data loading strategy
5. Define validation checks
6. Estimate migration time and resources

The plan should include:
- DDL scripts for Snowflake
- Type mapping decisions
- Data loading approach (CSV/Parquet, parallelism)
- Validation strategy
- Rollback procedures
"""
    
    else:
        return f"Prompt not found: {name}"


async def main():
    """
    Main entry point for MCP server.
    """
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
