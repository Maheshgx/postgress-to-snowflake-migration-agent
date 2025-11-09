"""
FastAPI backend for PostgreSQL to Snowflake Migration Agent.
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, Optional
import os
from datetime import datetime
from backend.models import (
    MigrationRequest, MigrationResponse, MigrationProgress, 
    MigrationStatus, HealthResponse
)
from backend.migrator import MigrationOrchestrator
from backend.config import settings
from backend.logger import get_logger

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="PostgreSQL to Snowflake Migration Agent",
    description="Web-hosted migration agent with Okta SSO support",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active migrations (in production, use Redis or similar)
active_migrations: Dict[str, MigrationOrchestrator] = {}


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/api/v1/migrate", response_model=MigrationResponse)
async def start_migration(request: MigrationRequest, background_tasks: BackgroundTasks):
    """
    Start a new migration or continue an existing one.
    
    - If dry_run=true: Analyzes and plans without execution
    - If confirm=false: Generates plan and waits for confirmation
    - If confirm=true: Executes the migration
    """
    try:
        logger.info("Received migration request", 
                   postgres_host=request.postgres.host,
                   snowflake_account=request.snowflake.account,
                   dry_run=request.preferences.dry_run,
                   confirm=request.control.confirm)
        
        # Create orchestrator
        orchestrator = MigrationOrchestrator(request)
        run_id = orchestrator.run_id
        
        # Store in active migrations
        active_migrations[run_id] = orchestrator
        
        # Run migration in background
        background_tasks.add_task(run_migration_background, orchestrator)
        
        # Determine response message
        if request.preferences.dry_run:
            message = "Dry run started. Analysis and planning will be performed without execution."
            next_steps = [
                "Monitor progress at /api/v1/migrate/{run_id}/progress",
                "Review generated artifacts",
                "Re-run with dry_run=false and confirm=true to execute"
            ]
        elif request.control.confirm:
            message = "Migration started. Data will be migrated to Snowflake."
            next_steps = [
                "Monitor progress at /api/v1/migrate/{run_id}/progress",
                "Review validation results after completion",
                "Check summary.md for detailed report"
            ]
        else:
            message = "Analysis and planning started. No data will be migrated yet."
            next_steps = [
                "Monitor progress at /api/v1/migrate/{run_id}/progress",
                "Review generated plan and artifacts",
                "Re-run with confirm=true to execute migration"
            ]
        
        return MigrationResponse(
            run_id=run_id,
            status=MigrationStatus.PENDING,
            message=message,
            next_steps=next_steps
        )
    
    except Exception as e:
        logger.error(f"Failed to start migration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def run_migration_background(orchestrator: MigrationOrchestrator):
    """Run migration in background task."""
    try:
        result = orchestrator.run_complete()
        logger.info(f"Migration {orchestrator.run_id} completed", result=result)
    except Exception as e:
        logger.error(f"Migration {orchestrator.run_id} failed", error=str(e))


@app.get("/api/v1/migrate/{run_id}/progress", response_model=MigrationProgress)
async def get_progress(run_id: str):
    """Get real-time migration progress."""
    if run_id not in active_migrations:
        raise HTTPException(status_code=404, detail=f"Migration {run_id} not found")
    
    orchestrator = active_migrations[run_id]
    return orchestrator.get_progress()


@app.get("/api/v1/migrate/{run_id}/status")
async def get_status(run_id: str):
    """Get detailed migration status and results."""
    if run_id not in active_migrations:
        raise HTTPException(status_code=404, detail=f"Migration {run_id} not found")
    
    orchestrator = active_migrations[run_id]
    
    return {
        "run_id": run_id,
        "status": orchestrator.status.value,
        "artifacts_dir": orchestrator.artifacts_dir,
        "analysis_complete": orchestrator.analysis_results is not None,
        "migration_results": orchestrator.migration_results,
        "validation_results": orchestrator.validation_results,
        "log_entry_count": len(orchestrator.log_entries)
    }


@app.get("/api/v1/migrate/{run_id}/artifacts")
async def list_artifacts(run_id: str):
    """List all generated artifacts for a migration."""
    if run_id not in active_migrations:
        raise HTTPException(status_code=404, detail=f"Migration {run_id} not found")
    
    orchestrator = active_migrations[run_id]
    artifacts_dir = orchestrator.artifacts_dir
    
    if not os.path.exists(artifacts_dir):
        return {"artifacts": []}
    
    artifacts = []
    for filename in os.listdir(artifacts_dir):
        filepath = os.path.join(artifacts_dir, filename)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            artifacts.append({
                "filename": filename,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "download_url": f"/api/v1/migrate/{run_id}/artifacts/{filename}"
            })
    
    return {"artifacts": artifacts}


@app.get("/api/v1/migrate/{run_id}/artifacts/{filename}")
async def download_artifact(run_id: str, filename: str):
    """Download a specific artifact file."""
    if run_id not in active_migrations:
        raise HTTPException(status_code=404, detail=f"Migration {run_id} not found")
    
    orchestrator = active_migrations[run_id]
    filepath = os.path.join(orchestrator.artifacts_dir, filename)
    
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail=f"Artifact {filename} not found")
    
    # Determine media type
    media_type = "application/octet-stream"
    if filename.endswith('.json'):
        media_type = "application/json"
    elif filename.endswith('.yml') or filename.endswith('.yaml'):
        media_type = "application/x-yaml"
    elif filename.endswith('.sql'):
        media_type = "text/plain"
    elif filename.endswith('.md'):
        media_type = "text/markdown"
    elif filename.endswith('.ndjson'):
        media_type = "application/x-ndjson"
    
    return FileResponse(
        filepath,
        media_type=media_type,
        filename=filename
    )


@app.get("/api/v1/migrate/{run_id}/logs")
async def get_logs(run_id: str, limit: Optional[int] = 100, level: Optional[str] = None):
    """Get migration logs."""
    if run_id not in active_migrations:
        raise HTTPException(status_code=404, detail=f"Migration {run_id} not found")
    
    orchestrator = active_migrations[run_id]
    logs = orchestrator.log_entries
    
    # Filter by level if specified
    if level:
        logs = [log for log in logs if log.get('level', '').upper() == level.upper()]
    
    # Apply limit
    logs = logs[-limit:] if limit else logs
    
    return {"logs": logs, "total": len(orchestrator.log_entries)}


@app.post("/api/v1/migrate/{run_id}/cancel")
async def cancel_migration(run_id: str):
    """Cancel an active migration."""
    if run_id not in active_migrations:
        raise HTTPException(status_code=404, detail=f"Migration {run_id} not found")
    
    orchestrator = active_migrations[run_id]
    
    # In a full implementation, this would signal the background task to stop
    # For now, we just update the status
    orchestrator.status = MigrationStatus.CANCELLED
    orchestrator.log('INFO', 'control', 'Migration cancelled by user')
    
    return {
        "run_id": run_id,
        "status": "cancelled",
        "message": "Migration cancellation requested"
    }


@app.delete("/api/v1/migrate/{run_id}")
async def delete_migration(run_id: str):
    """Delete a migration and its artifacts."""
    if run_id not in active_migrations:
        raise HTTPException(status_code=404, detail=f"Migration {run_id} not found")
    
    orchestrator = active_migrations[run_id]
    
    # Only allow deletion of completed or failed migrations
    if orchestrator.status not in [MigrationStatus.COMPLETED, MigrationStatus.FAILED, MigrationStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete active migration. Cancel it first."
        )
    
    # Delete artifacts directory
    import shutil
    if os.path.exists(orchestrator.artifacts_dir):
        shutil.rmtree(orchestrator.artifacts_dir)
    
    if os.path.exists(orchestrator.temp_dir):
        shutil.rmtree(orchestrator.temp_dir)
    
    # Remove from active migrations
    del active_migrations[run_id]
    
    return {
        "run_id": run_id,
        "message": "Migration deleted successfully"
    }


@app.get("/api/v1/migrations")
async def list_migrations():
    """List all migrations."""
    migrations = []
    
    for run_id, orchestrator in active_migrations.items():
        progress = orchestrator.get_progress()
        migrations.append({
            "run_id": run_id,
            "status": orchestrator.status.value,
            "progress_percent": progress.progress_percent,
            "tables_completed": progress.tables_completed,
            "tables_total": progress.tables_total,
            "created_at": orchestrator.log_entries[0]['ts'] if orchestrator.log_entries else None
        })
    
    return {"migrations": migrations}


@app.post("/api/v1/test-connections")
async def test_connections(request: MigrationRequest):
    """Test database connections without starting migration."""
    results = {
        "postgres": {"status": "unknown", "message": ""},
        "snowflake": {"status": "unknown", "message": ""}
    }
    
    # Test PostgreSQL connection
    try:
        from backend.postgres_analyzer import PostgresAnalyzer
        analyzer = PostgresAnalyzer(request.postgres)
        analyzer.connect()
        analyzer.disconnect()
        results["postgres"] = {
            "status": "success",
            "message": f"Connected to PostgreSQL: {request.postgres.host}:{request.postgres.port}/{request.postgres.database}"
        }
    except Exception as e:
        results["postgres"] = {
            "status": "error",
            "message": str(e)
        }
    
    # Test Snowflake connection
    try:
        from backend.data_pipeline import SnowflakeLoader
        loader = SnowflakeLoader(request.snowflake, request.auth.access_token, request.preferences)
        loader.connect()
        loader.disconnect()
        results["snowflake"] = {
            "status": "success",
            "message": f"Connected to Snowflake: {request.snowflake.account}"
        }
    except Exception as e:
        results["snowflake"] = {
            "status": "error",
            "message": str(e)
        }
    
    return results


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
