"""
Data extraction and loading pipeline.
Handles extracting data from PostgreSQL, chunking, and loading to Snowflake.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import snowflake.connector
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from typing import Dict, List, Any, Optional
import os
import gzip
import io
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.models import PostgresConfig, SnowflakeConfig, MigrationPreferences, DataFormat
from backend.logger import get_logger

logger = get_logger(__name__)


class DataExtractor:
    """Extracts data from PostgreSQL tables."""
    
    def __init__(self, config: PostgresConfig, preferences: MigrationPreferences, temp_path: str):
        self.config = config
        self.preferences = preferences
        self.temp_path = temp_path
        self.conn = None
    
    def connect(self):
        """Establish PostgreSQL connection."""
        ssl_params = {}
        if self.config.ssl:
            ssl_params['sslmode'] = self.config.ssl.mode.value
            if self.config.ssl.ca:
                ssl_params['sslrootcert'] = self.config.ssl.ca
        
        self.conn = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.username,
            password=self.config.password,
            **ssl_params
        )
        logger.info("Connected to PostgreSQL for data extraction")
    
    def disconnect(self):
        """Close PostgreSQL connection."""
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from PostgreSQL")
    
    def get_table_count(self, schema: str, table: str) -> int:
        """Get exact row count for a table."""
        with self.conn.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
            return cur.fetchone()[0]
    
    def extract_table_to_csv(self, schema: str, table: str, columns: List[str],
                             chunk_size: int = 100000) -> List[str]:
        """
        Extract table data to CSV file(s), chunked by max_chunk_mb.
        Returns list of generated file paths.
        """
        logger.info(f"Extracting {schema}.{table} to CSV")
        
        files = []
        quoted_columns = [f'"{col}"' for col in columns]
        column_list = ', '.join(quoted_columns)
        
        try:
            with self.conn.cursor('server_side_cursor') as cur:
                cur.itersize = chunk_size
                cur.execute(f'SELECT {column_list} FROM "{schema}"."{table}"')
                
                chunk_num = 0
                rows_in_chunk = 0
                current_file = None
                current_buffer = None
                current_gz = None
                
                for row in cur:
                    # Start new chunk if needed
                    if current_buffer is None:
                        chunk_num += 1
                        file_path = os.path.join(
                            self.temp_path,
                            f"{schema}_{table}_chunk_{chunk_num:04d}.csv.gz"
                        )
                        current_file = file_path
                        current_buffer = io.StringIO()
                        
                        # Write header
                        current_buffer.write(','.join(columns) + '\n')
                        rows_in_chunk = 0
                    
                    # Write row
                    row_data = []
                    for val in row:
                        if val is None:
                            row_data.append('')
                        elif isinstance(val, (dict, list)):
                            # JSON data
                            import json
                            row_data.append(f'"{json.dumps(val).replace(chr(34), chr(34)+chr(34))}"')
                        elif isinstance(val, str):
                            # Escape quotes
                            escaped = val.replace('"', '""')
                            row_data.append(f'"{escaped}"')
                        else:
                            row_data.append(str(val))
                    
                    current_buffer.write(','.join(row_data) + '\n')
                    rows_in_chunk += 1
                    
                    # Check if we should start a new chunk
                    if rows_in_chunk >= chunk_size:
                        # Compress and write
                        csv_data = current_buffer.getvalue()
                        with gzip.open(current_file, 'wt', encoding='utf-8') as gz_file:
                            gz_file.write(csv_data)
                        
                        files.append(current_file)
                        logger.info(f"Wrote chunk {chunk_num} with {rows_in_chunk} rows to {current_file}")
                        
                        # Reset for next chunk
                        current_buffer = None
                        current_file = None
                
                # Write final chunk if any data remains
                if current_buffer is not None and rows_in_chunk > 0:
                    csv_data = current_buffer.getvalue()
                    with gzip.open(current_file, 'wt', encoding='utf-8') as gz_file:
                        gz_file.write(csv_data)
                    
                    files.append(current_file)
                    logger.info(f"Wrote final chunk {chunk_num} with {rows_in_chunk} rows to {current_file}")
        
        except Exception as e:
            logger.error(f"Error extracting {schema}.{table}: {str(e)}")
            raise
        
        logger.info(f"Extracted {schema}.{table} to {len(files)} file(s)")
        return files
    
    def extract_table_to_parquet(self, schema: str, table: str, columns: List[str],
                                  chunk_size: int = 100000) -> List[str]:
        """
        Extract table data to Parquet file(s).
        Returns list of generated file paths.
        """
        logger.info(f"Extracting {schema}.{table} to Parquet")
        
        files = []
        quoted_columns = [f'"{col}"' for col in columns]
        column_list = ', '.join(quoted_columns)
        
        try:
            with self.conn.cursor('server_side_cursor') as cur:
                cur.itersize = chunk_size
                cur.execute(f'SELECT {column_list} FROM "{schema}"."{table}"')
                
                chunk_num = 0
                chunk_data = []
                
                for row in cur:
                    chunk_data.append(row)
                    
                    if len(chunk_data) >= chunk_size:
                        chunk_num += 1
                        file_path = os.path.join(
                            self.temp_path,
                            f"{schema}_{table}_chunk_{chunk_num:04d}.parquet"
                        )
                        
                        # Convert to pandas DataFrame
                        df = pd.DataFrame(chunk_data, columns=columns)
                        
                        # Write Parquet
                        df.to_parquet(file_path, compression='snappy', index=False)
                        
                        files.append(file_path)
                        logger.info(f"Wrote chunk {chunk_num} with {len(chunk_data)} rows to {file_path}")
                        
                        chunk_data = []
                
                # Write final chunk
                if chunk_data:
                    chunk_num += 1
                    file_path = os.path.join(
                        self.temp_path,
                        f"{schema}_{table}_chunk_{chunk_num:04d}.parquet"
                    )
                    
                    df = pd.DataFrame(chunk_data, columns=columns)
                    df.to_parquet(file_path, compression='snappy', index=False)
                    
                    files.append(file_path)
                    logger.info(f"Wrote final chunk {chunk_num} with {len(chunk_data)} rows to {file_path}")
        
        except Exception as e:
            logger.error(f"Error extracting {schema}.{table}: {str(e)}")
            raise
        
        logger.info(f"Extracted {schema}.{table} to {len(files)} file(s)")
        return files
    
    def extract_table(self, schema: str, table: str, columns: List[str]) -> List[str]:
        """Extract table data based on format preference."""
        if self.preferences.format == DataFormat.CSV:
            return self.extract_table_to_csv(schema, table, columns)
        else:
            return self.extract_table_to_parquet(schema, table, columns)


class SnowflakeLoader:
    """Loads data into Snowflake."""
    
    def __init__(self, config: SnowflakeConfig, auth_token: str, preferences: MigrationPreferences):
        self.config = config
        self.auth_token = auth_token
        self.preferences = preferences
        self.conn = None
        self.loaded_files = set()  # Track loaded files for idempotency
    
    def connect(self):
        """Establish Snowflake connection using OAuth token."""
        try:
            self.conn = snowflake.connector.connect(
                account=self.config.account,
                authenticator='oauth',
                token=self.auth_token,
                warehouse=self.config.warehouse,
                database=self.config.database,
                schema=self.config.schema,
                role=self.config.default_role
            )
            logger.info(f"Connected to Snowflake: {self.config.account}")
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {str(e)}")
            raise
    
    def disconnect(self):
        """Close Snowflake connection."""
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from Snowflake")
    
    def execute_ddl(self, ddl: str):
        """Execute DDL statement."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(ddl)
            cursor.close()
            logger.info("DDL executed successfully")
        except Exception as e:
            logger.error(f"DDL execution failed: {str(e)}")
            raise
    
    def execute_ddl_script(self, script: str):
        """Execute multi-statement DDL script."""
        statements = [s.strip() for s in script.split(';') if s.strip()]
        
        for statement in statements:
            if statement:
                try:
                    cursor = self.conn.cursor()
                    cursor.execute(statement)
                    cursor.close()
                except Exception as e:
                    logger.error(f"Failed to execute statement: {statement[:100]}...")
                    logger.error(f"Error: {str(e)}")
                    raise
        
        logger.info(f"Executed {len(statements)} DDL statements")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60))
    def upload_file_to_stage(self, file_path: str, stage_name: str) -> str:
        """Upload file to Snowflake stage with retry logic."""
        file_name = os.path.basename(file_path)
        
        try:
            cursor = self.conn.cursor()
            put_cmd = f"PUT file://{file_path} @{stage_name} AUTO_COMPRESS=FALSE OVERWRITE=FALSE"
            cursor.execute(put_cmd)
            result = cursor.fetchone()
            cursor.close()
            
            logger.info(f"Uploaded {file_name} to stage {stage_name}")
            return file_name
        except Exception as e:
            logger.error(f"Failed to upload {file_name}: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60))
    def copy_into_table(self, schema: str, table: str, stage_name: str,
                        file_pattern: str, file_format: str, columns: List[str]) -> Dict[str, Any]:
        """Execute COPY INTO command with retry logic."""
        full_table = f"{schema}.{table}"
        
        # Build column list
        column_list = ', '.join([f'"{col}"' for col in columns])
        
        try:
            cursor = self.conn.cursor()
            
            # COPY INTO command with MATCH_BY_COLUMN_NAME
            copy_cmd = f"""
                COPY INTO {full_table} ({column_list})
                FROM @{stage_name}
                FILES = ('{file_pattern}')
                FILE_FORMAT = {file_format}
                MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
                ON_ERROR = 'ABORT_STATEMENT'
                PURGE = FALSE
            """
            
            start_time = datetime.utcnow()
            cursor.execute(copy_cmd)
            results = cursor.fetchall()
            end_time = datetime.utcnow()
            
            cursor.close()
            
            # Parse results
            rows_loaded = 0
            for result in results:
                if result[1] == 'LOADED':
                    rows_loaded += result[3]
            
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            logger.info(f"Loaded {rows_loaded} rows into {full_table} from {file_pattern}")
            
            return {
                'table': full_table,
                'file': file_pattern,
                'rows_loaded': rows_loaded,
                'duration_ms': duration_ms,
                'status': 'success'
            }
        
        except Exception as e:
            logger.error(f"COPY INTO failed for {full_table}: {str(e)}")
            return {
                'table': full_table,
                'file': file_pattern,
                'rows_loaded': 0,
                'duration_ms': 0,
                'status': 'failed',
                'error': str(e)
            }
    
    def load_table(self, schema: str, table: str, file_paths: List[str],
                   columns: List[str]) -> List[Dict[str, Any]]:
        """Load all files for a table into Snowflake."""
        logger.info(f"Loading {len(file_paths)} files into {schema}.{table}")
        
        results = []
        
        # Upload files to stage
        uploaded_files = []
        for file_path in file_paths:
            try:
                staged_file = self.upload_file_to_stage(file_path, self.config.stage)
                uploaded_files.append(staged_file)
            except Exception as e:
                logger.error(f"Failed to upload {file_path}: {str(e)}")
                results.append({
                    'table': f"{schema}.{table}",
                    'file': os.path.basename(file_path),
                    'rows_loaded': 0,
                    'duration_ms': 0,
                    'status': 'upload_failed',
                    'error': str(e)
                })
        
        # Load files with COPY INTO
        for staged_file in uploaded_files:
            # Skip if already loaded (idempotency)
            if staged_file in self.loaded_files:
                logger.info(f"Skipping {staged_file} - already loaded")
                continue
            
            result = self.copy_into_table(
                schema, table, self.config.stage,
                staged_file, self.config.file_format, columns
            )
            results.append(result)
            
            if result['status'] == 'success':
                self.loaded_files.add(staged_file)
        
        return results


class MigrationPipeline:
    """Orchestrates the complete migration pipeline."""
    
    def __init__(self, postgres_config: PostgresConfig, snowflake_config: SnowflakeConfig,
                 auth_token: str, preferences: MigrationPreferences, temp_path: str):
        self.postgres_config = postgres_config
        self.snowflake_config = snowflake_config
        self.auth_token = auth_token
        self.preferences = preferences
        self.temp_path = temp_path
        
        self.extractor = DataExtractor(postgres_config, preferences, temp_path)
        self.loader = SnowflakeLoader(snowflake_config, auth_token, preferences)
    
    def migrate_table(self, schema: str, table: str, columns: List[str]) -> Dict[str, Any]:
        """Migrate a single table."""
        logger.info(f"Starting migration of {schema}.{table}")
        
        start_time = datetime.utcnow()
        
        try:
            # Extract data
            file_paths = self.extractor.extract_table(schema, table, columns)
            
            # Load data
            load_results = self.loader.load_table(schema, table, file_paths, columns)
            
            # Aggregate results
            total_rows = sum(r['rows_loaded'] for r in load_results)
            total_duration = sum(r['duration_ms'] for r in load_results)
            
            end_time = datetime.utcnow()
            total_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                'schema': schema,
                'table': table,
                'status': 'completed',
                'rows_loaded': total_rows,
                'file_count': len(file_paths),
                'duration_ms': total_time_ms,
                'load_results': load_results
            }
        
        except Exception as e:
            logger.error(f"Migration failed for {schema}.{table}: {str(e)}")
            return {
                'schema': schema,
                'table': table,
                'status': 'failed',
                'error': str(e)
            }
    
    def migrate_schema(self, schema: str, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Migrate all tables in a schema with parallelism."""
        logger.info(f"Migrating schema {schema} with {len(tables)} tables")
        
        results = []
        
        # Connect to both databases
        self.extractor.connect()
        self.loader.connect()
        
        try:
            # Use ThreadPoolExecutor for parallel table migrations
            with ThreadPoolExecutor(max_workers=self.preferences.parallelism) as executor:
                future_to_table = {}
                
                for table_detail in tables:
                    table_name = table_detail['table_name']
                    columns = [col['column_name'] for col in table_detail['columns']]
                    
                    future = executor.submit(self.migrate_table, schema, table_name, columns)
                    future_to_table[future] = table_name
                
                for future in as_completed(future_to_table):
                    table_name = future_to_table[future]
                    try:
                        result = future.result()
                        results.append(result)
                        logger.info(f"Completed migration of {schema}.{table_name}")
                    except Exception as e:
                        logger.error(f"Failed to migrate {schema}.{table_name}: {str(e)}")
                        results.append({
                            'schema': schema,
                            'table': table_name,
                            'status': 'failed',
                            'error': str(e)
                        })
        
        finally:
            self.extractor.disconnect()
            self.loader.disconnect()
        
        return results
