"""
Pydantic models for request/response schemas.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class SSLMode(str, Enum):
    """PostgreSQL SSL modes."""
    DISABLE = "disable"
    ALLOW = "allow"
    PREFER = "prefer"
    REQUIRE = "require"
    VERIFY_CA = "verify-ca"
    VERIFY_FULL = "verify-full"


class DataFormat(str, Enum):
    """Data export format."""
    CSV = "CSV"
    PARQUET = "PARQUET"


class CaseStyle(str, Enum):
    """Identifier case style."""
    UPPER = "UPPER"
    LOWER = "LOWER"
    PRESERVE = "PRESERVE"


class PostgresSSLConfig(BaseModel):
    """PostgreSQL SSL configuration."""
    mode: SSLMode = SSLMode.PREFER
    ca: Optional[str] = Field(None, description="CA certificate path or content")


class PostgresConfig(BaseModel):
    """PostgreSQL connection configuration."""
    host: str = Field(..., description="PostgreSQL host")
    port: int = Field(5432, ge=1, le=65535)
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    schemas: List[str] = Field(default=["*"], description="List of schemas to migrate or ['*'] for all")
    ssl: Optional[PostgresSSLConfig] = Field(None, description="SSL configuration")


class SnowflakeConfig(BaseModel):
    """Snowflake connection configuration."""
    account: str = Field(..., description="Snowflake account identifier")
    warehouse: str = Field(..., description="Warehouse name")
    database: str = Field(..., description="Target database")
    default_role: str = Field(..., description="Default role for operations")
    schema: str = Field("PUBLIC", description="Target schema")
    stage: str = Field(..., description="Named stage for file uploads")
    file_format: str = Field(..., description="Named file format")


class OAuthConfig(BaseModel):
    """OAuth authentication configuration."""
    access_token: str = Field(..., description="Okta External OAuth access token")


class MigrationPreferences(BaseModel):
    """Migration preferences and options."""
    format: DataFormat = DataFormat.CSV
    max_chunk_mb: int = Field(200, ge=1, le=1000, description="Maximum chunk size in MB")
    parallelism: int = Field(4, ge=1, le=16, description="Parallel operations")
    use_identity_for_serial: bool = Field(True, description="Use IDENTITY for serial columns")
    cluster_key_hints: Dict[str, List[str]] = Field(default_factory=dict, description="Table -> columns for cluster keys")
    case_style: CaseStyle = Field(CaseStyle.UPPER, description="Identifier naming convention")
    dry_run: bool = Field(False, description="Generate plan without executing")


class MigrationControl(BaseModel):
    """Migration control flags."""
    run_id: Optional[str] = Field(None, description="Unique run identifier")
    confirm: bool = Field(False, description="Explicit confirmation to execute migration")


class MigrationRequest(BaseModel):
    """Complete migration request payload."""
    postgres: PostgresConfig
    snowflake: SnowflakeConfig
    auth: OAuthConfig
    preferences: MigrationPreferences = Field(default_factory=MigrationPreferences)
    control: MigrationControl = Field(default_factory=MigrationControl)


class MigrationStatus(str, Enum):
    """Migration execution status."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EXECUTING = "executing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TableStatus(BaseModel):
    """Status of a single table migration."""
    table_name: str
    schema_name: str
    status: str
    rows_loaded: Optional[int] = None
    bytes_processed: Optional[int] = None
    duration_ms: Optional[int] = None
    retries: int = 0
    error: Optional[str] = None


class MigrationProgress(BaseModel):
    """Real-time migration progress."""
    run_id: str
    status: MigrationStatus
    phase: str
    progress_percent: float = Field(0.0, ge=0, le=100)
    tables_completed: int = 0
    tables_total: int = 0
    current_operation: Optional[str] = None
    table_statuses: List[TableStatus] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class MigrationResponse(BaseModel):
    """Migration API response."""
    run_id: str
    status: MigrationStatus
    message: str
    artifacts: List[str] = Field(default_factory=list, description="Generated artifact files")
    next_steps: Optional[List[str]] = Field(None, description="Recommended next actions")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str
