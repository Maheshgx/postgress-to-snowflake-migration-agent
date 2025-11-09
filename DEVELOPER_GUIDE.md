# Developer Guide

Comprehensive code walkthrough for the PostgreSQL to Snowflake Migration Agent.

## Table of Contents

1. [Introduction](#introduction)
2. [Development Setup](#development-setup)
3. [Codebase Structure](#codebase-structure)
4. [Backend Code Walkthrough](#backend-code-walkthrough)
5. [Frontend Code Walkthrough](#frontend-code-walkthrough)
6. [Extension Points](#extension-points)
7. [Testing](#testing)
8. [Best Practices](#best-practices)

---

## Introduction

### Technology Stack

**Backend:**
- Python 3.11+ with async/await
- FastAPI for REST API
- Pydantic for data validation
- psycopg2 for PostgreSQL
- snowflake-connector-python
- Pandas/PyArrow for data processing
- Structlog for structured logging

**Frontend:**
- React 18 with TypeScript
- TailwindCSS for styling
- Vite for build tooling
- Axios for HTTP requests

---

## Development Setup

### Backend Setup

```bash
# Clone repository
git clone https://github.com/Maheshgx/postgress-to-snowflake-migration-agent.git
cd postgress-to-snowflake-migration-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install black isort mypy pytest pytest-asyncio

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run backend
cd backend
python -m uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev  # Development server on port 5173
```

---

## Codebase Structure

```
postgress-to-snowflake-migration-agent/
├── backend/
│   ├── main.py                    # FastAPI app & REST endpoints
│   ├── config.py                  # Configuration management
│   ├── models.py                  # Pydantic data models
│   ├── logger.py                  # Structured logging
│   ├── postgres_analyzer.py       # PostgreSQL introspection
│   ├── snowflake_generator.py     # DDL generation & type mapping
│   ├── data_pipeline.py           # ETL pipeline
│   ├── validation.py              # Post-migration validation
│   └── migrator.py                # Migration orchestration
├── frontend/
│   └── src/
│       ├── App.tsx                # Main application
│       ├── components/
│       │   ├── ConfigurationForm.tsx
│       │   ├── MigrationProgress.tsx
│       │   └── ArtifactsViewer.tsx
│       └── index.css
└── requirements.txt
```

---

## Backend Code Walkthrough

### 1. Entry Point: `main.py`

**Purpose:** FastAPI application with REST endpoints

#### Key Components

```python
# FastAPI app initialization
app = FastAPI(
    title="PostgreSQL to Snowflake Migration Agent",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"]
)
```

#### Core Endpoints

**Start Migration:**
```python
@app.post("/api/v1/migrate")
async def start_migration(
    request: MigrationRequest,
    background_tasks: BackgroundTasks
) -> MigrationResponse:
    """
    1. Generate unique run_id
    2. Validate request
    3. Launch background task
    4. Return immediately
    """
    run_id = str(uuid.uuid4())
    background_tasks.add_task(execute_migration, run_id, request)
    return MigrationResponse(run_id=run_id, status="pending")
```

**Get Progress:**
```python
@app.get("/api/v1/migrate/{run_id}/progress")
async def get_progress(run_id: str) -> MigrationProgress:
    """Real-time progress polling (called every 2 seconds)"""
    return migrations[run_id]
```

**Background Task:**
```python
async def execute_migration(run_id: str, request: MigrationRequest):
    """
    Migration phases:
    1. ANALYZE - PostgreSQL introspection
    2. PLAN - DDL generation
    3. EXECUTE - Data migration (if not dry-run)
    4. VALIDATE - Data quality checks
    5. REPORT - Generate artifacts
    """
    orchestrator = MigrationOrchestrator(run_id, request)
    await orchestrator.run()
```

---

### 2. Configuration: `config.py`

**Purpose:** Environment-based configuration

```python
class Settings(BaseSettings):
    """Loads from environment variables with defaults"""
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    artifacts_path: str = "./artifacts"
    
    class Config:
        env_file = ".env"
```

**Usage:**
```python
from backend.config import settings
path = settings.artifacts_path
```

---

### 3. Data Models: `models.py`

**Purpose:** Pydantic models for validation

#### Key Models

```python
class PostgresConfig(BaseModel):
    host: str
    port: int = 5432
    database: str
    username: str
    password: str
    schemas: List[str] = ["*"]

class SnowflakeConfig(BaseModel):
    account: str
    warehouse: str
    database: str
    default_role: str
    stage: str
    file_format: str

class MigrationRequest(BaseModel):
    postgres: PostgresConfig
    snowflake: SnowflakeConfig
    auth: OAuthConfig
    preferences: MigrationPreferences

class MigrationProgress(BaseModel):
    run_id: str
    status: MigrationStatus
    phase: str
    progress_percent: float
    tables_completed: int
    tables_total: int
```

---

### 4. PostgreSQL Analyzer: `postgres_analyzer.py`

**Purpose:** Introspect PostgreSQL database

#### Core Methods

```python
class PostgresAnalyzer:
    def analyze(self) -> Dict[str, Any]:
        """Main analysis entry point"""
        return {
            "database_info": self.get_database_info(),
            "schemas": self.get_schemas(),
            "tables": self.get_all_tables(),
            "volumetrics": self.calculate_volumetrics()
        }
    
    def get_tables(self, schema: str) -> List[Dict]:
        """Query information_schema.tables"""
        query = """
            SELECT table_name, table_type,
                   pg_class.reltuples AS estimated_rows
            FROM information_schema.tables t
            LEFT JOIN pg_class ON pg_class.relname = t.table_name
            WHERE table_schema = %s
        """
    
    def get_columns(self, schema: str, table: str) -> List[Dict]:
        """Query information_schema.columns"""
        query = """
            SELECT column_name, data_type,
                   is_nullable, column_default,
                   character_maximum_length,
                   numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
        """
    
    def get_constraints(self, schema: str, table: str) -> Dict:
        """Extract PRIMARY KEY, UNIQUE, FOREIGN KEY, CHECK"""
        # Queries table_constraints, key_column_usage
```

---

### 5. Snowflake Generator: `snowflake_generator.py`

**Purpose:** Generate Snowflake DDL and map types

#### Type Mapping

```python
class TypeMapper:
    def map_type(self, pg_type: str, **kwargs) -> Tuple[str, str]:
        """
        PostgreSQL → Snowflake type mapping
        
        Returns: (snowflake_type, rationale)
        
        Examples:
            INTEGER → NUMBER(10,0)
            VARCHAR(n) → VARCHAR(n)
            JSONB → VARIANT
            BYTEA → BINARY
            UUID → VARCHAR(36)
        """
```

#### DDL Generation

```python
class SnowflakeGenerator:
    def generate_ddl(self) -> str:
        """
        Generate complete DDL:
        1. CREATE DATABASE
        2. CREATE SCHEMA
        3. CREATE STAGE
        4. CREATE FILE FORMAT
        5. CREATE TABLEs with constraints
        """
    
    def generate_table_ddl(self, table: Dict) -> str:
        """
        CREATE TABLE with:
        - Column definitions
        - NOT NULL constraints
        - Primary keys (metadata)
        - Identity columns
        - Comments
        """
```

---

### 6. Data Pipeline: `data_pipeline.py`

**Purpose:** Extract data from PostgreSQL and load to Snowflake

#### Data Extractor

```python
class DataExtractor:
    def extract_table_to_csv(
        self, 
        schema: str, 
        table: str,
        output_path: str
    ) -> List[str]:
        """
        Extract table data to CSV files
        
        Features:
        - Server-side cursors (low memory)
        - Chunking (configurable size)
        - GZIP compression
        - Progress tracking
        """
        # Use named cursor for streaming
        cursor = conn.cursor(name='extract_cursor')
        cursor.itersize = 10000
        
        # Execute query
        cursor.execute(f"SELECT * FROM {schema}.{table}")
        
        # Chunk and write to CSV
        while True:
            rows = cursor.fetchmany(chunk_size)
            if not rows:
                break
            # Write to CSV with gzip
```

#### Snowflake Loader

```python
class SnowflakeLoader:
    def upload_file_to_stage(self, local_file: str, stage_path: str):
        """Upload file using PUT command"""
        cursor.execute(f"PUT file://{local_file} @{stage_path}")
    
    def copy_into_table(
        self, 
        table: str, 
        stage_files: List[str]
    ):
        """
        Load data using COPY INTO
        
        Features:
        - MATCH_BY_COLUMN_NAME
        - Error handling
        - File pattern matching
        """
        copy_sql = f"""
            COPY INTO {table}
            FROM @{stage}
            FILES = ({file_list})
            FILE_FORMAT = {file_format}
            MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
            ON_ERROR = 'ABORT_STATEMENT'
        """
```

---

### 7. Validation: `validation.py`

**Purpose:** Post-migration data validation

```python
class Validator:
    def validate_migration(self) -> Dict[str, Any]:
        """
        Run validation checks:
        1. Row count comparison
        2. NOT NULL constraints
        3. Primary key duplicates
        4. JSON validity
        """
    
    def validate_row_counts(self, table: str) -> Dict:
        """Compare row counts between source and target"""
        pg_count = self.execute_pg_query(
            f"SELECT COUNT(*) FROM {table}"
        )
        sf_count = self.execute_sf_query(
            f"SELECT COUNT(*) FROM {table}"
        )
        return {
            "source_count": pg_count,
            "target_count": sf_count,
            "match": pg_count == sf_count
        }
```

---

### 8. Orchestrator: `migrator.py`

**Purpose:** Coordinate migration phases

```python
class MigrationOrchestrator:
    async def run(self):
        """Execute migration phases in order"""
        try:
            await self.phase_analyze()
            await self.phase_plan()
            
            if not self.dry_run:
                await self.phase_execute()
                await self.phase_validate()
            
            await self.phase_report()
        except Exception as e:
            self.handle_error(e)
    
    async def phase_analyze(self):
        """Analyze PostgreSQL database"""
        self.update_progress(status="analyzing")
        analyzer = PostgresAnalyzer(self.pg_config)
        self.analysis = analyzer.analyze()
    
    async def phase_execute(self):
        """Execute data migration with parallelism"""
        with ThreadPoolExecutor(max_workers=self.parallelism) as executor:
            futures = [
                executor.submit(self.migrate_table, table)
                for table in self.tables
            ]
```

---

## Frontend Code Walkthrough

### Main Application: `App.tsx`

```tsx
function App() {
  const [currentStep, setCurrentStep] = useState(0);
  const [migrationRunId, setMigrationRunId] = useState<string | null>(null);
  
  // Steps: Configure → Progress → Artifacts
  
  const handleStartMigration = async (config: MigrationRequest) => {
    const response = await axios.post('/api/v1/migrate', config);
    setMigrationRunId(response.data.run_id);
    setCurrentStep(1); // Move to progress view
  };
  
  return (
    <div className="min-h-screen bg-gray-50">
      {currentStep === 0 && (
        <ConfigurationForm onSubmit={handleStartMigration} />
      )}
      {currentStep === 1 && migrationRunId && (
        <MigrationProgress runId={migrationRunId} />
      )}
      {currentStep === 2 && migrationRunId && (
        <ArtifactsViewer runId={migrationRunId} />
      )}
    </div>
  );
}
```

### Configuration Form: `ConfigurationForm.tsx`

```tsx
function ConfigurationForm({ onSubmit }) {
  const [config, setConfig] = useState<MigrationRequest>({
    postgres: { host: '', port: 5432, ... },
    snowflake: { account: '', ... },
    auth: { access_token: '' },
    preferences: { format: 'CSV', parallelism: 4 }
  });
  
  const handleTestConnections = async () => {
    await axios.post('/api/v1/test-connections', config);
    // Show success/failure
  };
  
  return (
    <form onSubmit={() => onSubmit(config)}>
      {/* PostgreSQL fields */}
      {/* Snowflake fields */}
      {/* Preferences */}
      <button onClick={handleTestConnections}>Test Connections</button>
      <button type="submit">Start Migration</button>
    </form>
  );
}
```

### Progress Display: `MigrationProgress.tsx`

```tsx
function MigrationProgress({ runId }) {
  const [progress, setProgress] = useState<MigrationProgress | null>(null);
  
  useEffect(() => {
    // Poll for progress every 2 seconds
    const interval = setInterval(async () => {
      const response = await axios.get(`/api/v1/migrate/${runId}/progress`);
      setProgress(response.data);
      
      if (response.data.status === 'completed' || response.data.status === 'failed') {
        clearInterval(interval);
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, [runId]);
  
  return (
    <div>
      <h2>Migration Progress: {progress?.progress_percent}%</h2>
      <div className="progress-bar">
        <div style={{ width: `${progress?.progress_percent}%` }} />
      </div>
      
      {/* Table status list */}
      {progress?.table_statuses.map(table => (
        <div key={table.table_name}>
          {table.table_name}: {table.status}
        </div>
      ))}
    </div>
  );
}
```

---

## Extension Points

### 1. Adding New Type Mappings

**File:** `snowflake_generator.py`

```python
def map_type(self, pg_type: str, **kwargs):
    # Add new mapping
    elif pg_type == "custom_type":
        return "VARIANT", "Custom type → VARIANT"
```

### 2. Adding Custom Validations

**File:** `validation.py`

```python
class Validator:
    def custom_validation(self, table: str):
        """Add your custom validation logic"""
        pass
    
    def validate_migration(self):
        # Add to validation suite
        results = {
            **existing_validations,
            "custom": self.custom_validation(table)
        }
```

### 3. Supporting New Data Formats

**File:** `data_pipeline.py`

```python
class DataExtractor:
    def extract_table_to_avro(self, schema, table):
        """Add Avro format support"""
        pass
```

### 4. Adding New API Endpoints

**File:** `main.py`

```python
@app.post("/api/v1/custom-endpoint")
async def custom_endpoint(data: CustomModel):
    """Add new endpoint"""
    pass
```

---

## Testing

### Unit Tests

```bash
# Install pytest
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest backend/tests/ -v

# With coverage
pytest backend/tests/ --cov=backend --cov-report=html
```

### Test Structure

```python
# test_analyzer.py
import pytest
from backend.postgres_analyzer import PostgresAnalyzer

def test_type_mapping():
    mapper = TypeMapper()
    sf_type, rationale = mapper.map_type("integer")
    assert sf_type == "NUMBER(10,0)"

@pytest.mark.asyncio
async def test_migration_flow():
    # Test complete migration
    pass
```

### Integration Tests

```python
# test_integration.py
def test_end_to_end_migration(test_db, test_snowflake):
    """Test complete migration flow"""
    request = MigrationRequest(...)
    response = client.post("/api/v1/migrate", json=request.dict())
    assert response.status_code == 200
```

---

## Best Practices

### 1. Error Handling

```python
try:
    result = risky_operation()
except SpecificException as e:
    logger.error("operation_failed", error=str(e), context={...})
    raise HTTPException(status_code=500, detail=str(e))
```

### 2. Logging

```python
# Always use structured logging
logger.info(
    "table_migrated",
    run_id=run_id,
    schema=schema,
    table=table,
    rows=row_count,
    duration_ms=duration
)
```

### 3. Resource Management

```python
# Use context managers
with psycopg2.connect(**params) as conn:
    with conn.cursor() as cursor:
        cursor.execute(query)

# Close connections
finally:
    if connection:
        connection.close()
```

### 4. Type Hints

```python
def process_table(
    schema: str,
    table: str,
    config: MigrationConfig
) -> Dict[str, Any]:
    """Always use type hints"""
    pass
```

### 5. Code Formatting

```bash
# Use black for formatting
black backend/

# Use isort for imports
isort backend/

# Use mypy for type checking
mypy backend/ --strict
```

---

## Common Development Tasks

### Adding a New Configuration Option

1. Add to `MigrationPreferences` in `models.py`
2. Update frontend form in `ConfigurationForm.tsx`
3. Use in relevant backend module

### Debugging Migration Issues

1. Set `LOG_LEVEL=DEBUG` in `.env`
2. Check `logs/run_log.ndjson` for structured logs
3. Review generated artifacts in `artifacts/`
4. Test connections independently

### Performance Optimization

1. Increase `parallelism` setting
2. Adjust `max_chunk_mb` for data size
3. Use Parquet format for large datasets
4. Scale up Snowflake warehouse

---

## Additional Resources

- **Architecture:** See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Setup:** See [SETUP.md](SETUP.md)
- **Usage:** See [USER_GUIDE.md](USER_GUIDE.md)
- **API Docs:** http://localhost:8000/docs (when running)

---

**Happy coding!** For questions or contributions, open an issue on GitHub.
