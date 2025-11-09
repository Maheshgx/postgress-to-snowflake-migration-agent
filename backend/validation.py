"""
Post-migration validation and reporting.
Verifies data integrity and generates comprehensive reports.
"""
import psycopg2
import snowflake.connector
from typing import Dict, List, Any, Tuple
from datetime import datetime
from backend.models import PostgresConfig, SnowflakeConfig
from backend.logger import get_logger

logger = get_logger(__name__)


class DataValidator:
    """Validates migrated data between PostgreSQL and Snowflake."""
    
    def __init__(self, pg_config: PostgresConfig, sf_config: SnowflakeConfig, auth_token: str):
        self.pg_config = pg_config
        self.sf_config = sf_config
        self.auth_token = auth_token
        self.pg_conn = None
        self.sf_conn = None
    
    def connect_postgres(self):
        """Connect to PostgreSQL."""
        ssl_params = {}
        if self.pg_config.ssl:
            ssl_params['sslmode'] = self.pg_config.ssl.mode.value
            if self.pg_config.ssl.ca:
                ssl_params['sslrootcert'] = self.pg_config.ssl.ca
        
        self.pg_conn = psycopg2.connect(
            host=self.pg_config.host,
            port=self.pg_config.port,
            database=self.pg_config.database,
            user=self.pg_config.username,
            password=self.pg_config.password,
            **ssl_params
        )
        logger.info("Connected to PostgreSQL for validation")
    
    def connect_snowflake(self):
        """Connect to Snowflake."""
        self.sf_conn = snowflake.connector.connect(
            account=self.sf_config.account,
            authenticator='oauth',
            token=self.auth_token,
            warehouse=self.sf_config.warehouse,
            database=self.sf_config.database,
            schema=self.sf_config.schema,
            role=self.sf_config.default_role
        )
        logger.info("Connected to Snowflake for validation")
    
    def disconnect(self):
        """Disconnect from both databases."""
        if self.pg_conn:
            self.pg_conn.close()
        if self.sf_conn:
            self.sf_conn.close()
        logger.info("Disconnected from databases")
    
    def get_pg_row_count(self, schema: str, table: str) -> int:
        """Get row count from PostgreSQL."""
        with self.pg_conn.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
            return cur.fetchone()[0]
    
    def get_sf_row_count(self, schema: str, table: str) -> int:
        """Get row count from Snowflake."""
        cursor = self.sf_conn.cursor()
        cursor.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
        result = cursor.fetchone()[0]
        cursor.close()
        return result
    
    def validate_row_counts(self, schema: str, tables: List[str]) -> List[Dict[str, Any]]:
        """Validate row counts match between source and target."""
        logger.info(f"Validating row counts for {len(tables)} tables in schema {schema}")
        
        results = []
        
        for table in tables:
            try:
                pg_count = self.get_pg_row_count(schema, table)
                sf_count = self.get_sf_row_count(schema, table)
                
                matches = pg_count == sf_count
                
                result = {
                    'schema': schema,
                    'table': table,
                    'check': 'row_count',
                    'postgres_value': pg_count,
                    'snowflake_value': sf_count,
                    'matches': matches,
                    'status': 'PASS' if matches else 'FAIL',
                    'message': f'Row counts match ({pg_count})' if matches else f'Row count mismatch: PG={pg_count}, SF={sf_count}'
                }
                
                results.append(result)
                
                if not matches:
                    logger.warning(f"Row count mismatch for {schema}.{table}: PG={pg_count}, SF={sf_count}")
            
            except Exception as e:
                logger.error(f"Error validating {schema}.{table}: {str(e)}")
                results.append({
                    'schema': schema,
                    'table': table,
                    'check': 'row_count',
                    'status': 'ERROR',
                    'message': str(e)
                })
        
        return results
    
    def check_null_constraints(self, schema: str, table: str, not_null_columns: List[str]) -> Dict[str, Any]:
        """Check that NOT NULL constraints are satisfied in Snowflake."""
        logger.info(f"Checking NULL constraints for {schema}.{table}")
        
        violations = []
        
        for column in not_null_columns:
            try:
                cursor = self.sf_conn.cursor()
                cursor.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}" WHERE "{column}" IS NULL')
                null_count = cursor.fetchone()[0]
                cursor.close()
                
                if null_count > 0:
                    violations.append({
                        'column': column,
                        'null_count': null_count
                    })
            except Exception as e:
                logger.error(f"Error checking NULL constraint on {column}: {str(e)}")
        
        return {
            'schema': schema,
            'table': table,
            'check': 'not_null_constraints',
            'status': 'PASS' if not violations else 'FAIL',
            'violations': violations,
            'message': 'All NOT NULL constraints satisfied' if not violations else f'{len(violations)} columns have NULL violations'
        }
    
    def check_primary_key_duplicates(self, schema: str, table: str, pk_columns: List[str]) -> Dict[str, Any]:
        """Check for duplicate values in primary key columns."""
        if not pk_columns:
            return {
                'schema': schema,
                'table': table,
                'check': 'primary_key_duplicates',
                'status': 'SKIP',
                'message': 'No primary key defined'
            }
        
        logger.info(f"Checking for duplicate PKs in {schema}.{table}")
        
        try:
            pk_list = ', '.join([f'"{col}"' for col in pk_columns])
            
            cursor = self.sf_conn.cursor()
            cursor.execute(f'''
                SELECT {pk_list}, COUNT(*) as cnt
                FROM "{schema}"."{table}"
                GROUP BY {pk_list}
                HAVING COUNT(*) > 1
                LIMIT 10
            ''')
            
            duplicates = cursor.fetchall()
            cursor.close()
            
            if duplicates:
                return {
                    'schema': schema,
                    'table': table,
                    'check': 'primary_key_duplicates',
                    'status': 'FAIL',
                    'duplicate_count': len(duplicates),
                    'sample_duplicates': [dict(zip(pk_columns + ['count'], dup)) for dup in duplicates],
                    'message': f'Found {len(duplicates)} duplicate primary key combinations (showing first 10)'
                }
            else:
                return {
                    'schema': schema,
                    'table': table,
                    'check': 'primary_key_duplicates',
                    'status': 'PASS',
                    'message': 'No duplicate primary keys found'
                }
        
        except Exception as e:
            logger.error(f"Error checking PK duplicates: {str(e)}")
            return {
                'schema': schema,
                'table': table,
                'check': 'primary_key_duplicates',
                'status': 'ERROR',
                'message': str(e)
            }
    
    def check_json_validity(self, schema: str, table: str, json_columns: List[str]) -> Dict[str, Any]:
        """Check that JSON/VARIANT columns are valid."""
        if not json_columns:
            return {
                'schema': schema,
                'table': table,
                'check': 'json_validity',
                'status': 'SKIP',
                'message': 'No JSON columns'
            }
        
        logger.info(f"Checking JSON validity for {schema}.{table}")
        
        invalid_counts = {}
        
        for column in json_columns:
            try:
                cursor = self.sf_conn.cursor()
                # Try to parse JSON and count failures
                cursor.execute(f'''
                    SELECT COUNT(*)
                    FROM "{schema}"."{table}"
                    WHERE "{column}" IS NOT NULL
                      AND TRY_PARSE_JSON("{column}") IS NULL
                ''')
                invalid_count = cursor.fetchone()[0]
                cursor.close()
                
                if invalid_count > 0:
                    invalid_counts[column] = invalid_count
            
            except Exception as e:
                logger.error(f"Error checking JSON validity on {column}: {str(e)}")
        
        return {
            'schema': schema,
            'table': table,
            'check': 'json_validity',
            'status': 'PASS' if not invalid_counts else 'FAIL',
            'invalid_counts': invalid_counts,
            'message': 'All JSON values are valid' if not invalid_counts else f'{sum(invalid_counts.values())} invalid JSON values found'
        }
    
    def validate_table(self, schema: str, table: str, table_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run all validation checks on a table."""
        logger.info(f"Validating table {schema}.{table}")
        
        results = []
        
        # Extract metadata
        columns = table_metadata.get('columns', [])
        constraints = table_metadata.get('constraints', {})
        
        not_null_columns = [col['column_name'] for col in columns if col['is_nullable'] == 'NO']
        pk_columns = []
        if constraints.get('primary_keys'):
            pk_columns = constraints['primary_keys'][0].get('columns', [])
        
        json_columns = [
            col['column_name'] for col in columns 
            if col['data_type'] in ('json', 'jsonb') or 'json' in col['data_type'].lower()
        ]
        
        # Run checks
        results.append(self.validate_row_counts(schema, [table])[0])
        results.append(self.check_null_constraints(schema, table, not_null_columns))
        results.append(self.check_primary_key_duplicates(schema, table, pk_columns))
        results.append(self.check_json_validity(schema, table, json_columns))
        
        return results
    
    def generate_validation_sql(self, analysis: Dict[str, Any]) -> str:
        """Generate SQL script for post-migration validation checks."""
        lines = [
            "-- =============================================================================",
            "-- Post-Migration Validation Checks",
            f"-- Generated: {datetime.utcnow().isoformat()}",
            "-- =============================================================================",
            "",
            "-- Run these queries in Snowflake to validate the migration",
            ""
        ]
        
        for schema_detail in analysis['schemas']:
            schema_name = schema_detail['schema_name']
            
            lines.append(f"-- Schema: {schema_name}")
            lines.append("")
            
            for table_detail in schema_detail['tables']:
                table_name = table_detail['table_name']
                columns = table_detail['columns']
                constraints = table_detail['constraints']
                
                lines.append(f"-- Table: {schema_name}.{table_name}")
                lines.append("")
                
                # Row count check
                lines.append(f"-- Row count")
                lines.append(f"SELECT '{schema_name}.{table_name}' AS table_name, COUNT(*) AS row_count")
                lines.append(f"FROM \"{schema_name}\".\"{table_name}\";")
                lines.append("")
                
                # NOT NULL checks
                not_null_cols = [col['column_name'] for col in columns if col['is_nullable'] == 'NO']
                if not_null_cols:
                    lines.append(f"-- NOT NULL constraint violations")
                    for col in not_null_cols:
                        lines.append(f"SELECT '{schema_name}.{table_name}.{col}' AS column_name, COUNT(*) AS null_count")
                        lines.append(f"FROM \"{schema_name}\".\"{table_name}\"")
                        lines.append(f"WHERE \"{col}\" IS NULL;")
                        lines.append("")
                
                # Primary key duplicate check
                if constraints.get('primary_keys'):
                    pk_cols = constraints['primary_keys'][0]['columns']
                    pk_list = ', '.join([f'\"{col}\"' for col in pk_cols])
                    lines.append(f"-- Primary key duplicate check")
                    lines.append(f"SELECT {pk_list}, COUNT(*) AS duplicate_count")
                    lines.append(f"FROM \"{schema_name}\".\"{table_name}\"")
                    lines.append(f"GROUP BY {pk_list}")
                    lines.append(f"HAVING COUNT(*) > 1;")
                    lines.append("")
                
                # JSON validity check
                json_cols = [col['column_name'] for col in columns if col['data_type'] in ('json', 'jsonb')]
                if json_cols:
                    lines.append(f"-- JSON validity check")
                    for col in json_cols:
                        lines.append(f"SELECT '{schema_name}.{table_name}.{col}' AS column_name, COUNT(*) AS invalid_count")
                        lines.append(f"FROM \"{schema_name}\".\"{table_name}\"")
                        lines.append(f"WHERE \"{col}\" IS NOT NULL AND TRY_PARSE_JSON(\"{col}\") IS NULL;")
                        lines.append("")
                
                lines.append("")
        
        return "\n".join(lines)


class ReportGenerator:
    """Generates migration reports and summaries."""
    
    @staticmethod
    def generate_summary_markdown(run_id: str, analysis: Dict[str, Any], 
                                   migration_results: List[Dict[str, Any]],
                                   validation_results: List[Dict[str, Any]]) -> str:
        """Generate comprehensive migration summary report."""
        lines = [
            "# PostgreSQL to Snowflake Migration Summary",
            "",
            f"**Run ID:** `{run_id}`",
            f"**Timestamp:** {datetime.utcnow().isoformat()}",
            f"**Source Database:** {analysis['metadata']['database']}",
            "",
            "---",
            ""
        ]
        
        # Migration overview
        total_tables = sum(len(schema['tables']) for schema in analysis['schemas'])
        completed_tables = sum(1 for r in migration_results if r.get('status') == 'completed')
        failed_tables = sum(1 for r in migration_results if r.get('status') == 'failed')
        total_rows = sum(r.get('rows_loaded', 0) for r in migration_results)
        
        lines.extend([
            "## Migration Overview",
            "",
            f"- **Total Tables:** {total_tables}",
            f"- **Successfully Migrated:** {completed_tables}",
            f"- **Failed:** {failed_tables}",
            f"- **Total Rows Migrated:** {total_rows:,}",
            ""
        ])
        
        # Per-table results
        lines.extend([
            "## Table Migration Results",
            "",
            "| Schema | Table | Status | Rows Loaded | Duration | Files |",
            "|--------|-------|--------|-------------|----------|-------|"
        ])
        
        for result in migration_results:
            schema = result.get('schema', 'N/A')
            table = result.get('table', 'N/A')
            status = result.get('status', 'unknown')
            rows = result.get('rows_loaded', 0)
            duration_ms = result.get('duration_ms', 0)
            duration_sec = duration_ms / 1000 if duration_ms else 0
            file_count = result.get('file_count', 0)
            
            status_emoji = "✅" if status == 'completed' else "❌"
            lines.append(f"| {schema} | {table} | {status_emoji} {status} | {rows:,} | {duration_sec:.2f}s | {file_count} |")
        
        lines.append("")
        
        # Validation results
        if validation_results:
            lines.extend([
                "## Validation Results",
                "",
                "| Schema | Table | Check | Status | Message |",
                "|--------|-------|-------|--------|---------|"
            ])
            
            for result in validation_results:
                schema = result.get('schema', 'N/A')
                table = result.get('table', 'N/A')
                check = result.get('check', 'N/A')
                status = result.get('status', 'UNKNOWN')
                message = result.get('message', '')
                
                status_emoji = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "ERROR": "⚠️"}.get(status, "❓")
                lines.append(f"| {schema} | {table} | {check} | {status_emoji} {status} | {message} |")
            
            lines.append("")
            
            # Summary stats
            total_checks = len(validation_results)
            passed = sum(1 for r in validation_results if r.get('status') == 'PASS')
            failed = sum(1 for r in validation_results if r.get('status') == 'FAIL')
            skipped = sum(1 for r in validation_results if r.get('status') == 'SKIP')
            errors = sum(1 for r in validation_results if r.get('status') == 'ERROR')
            
            lines.extend([
                "### Validation Summary:",
                "",
                f"- **Total Checks:** {total_checks}",
                f"- **Passed:** ✅ {passed}",
                f"- **Failed:** ❌ {failed}",
                f"- **Skipped:** ⏭️ {skipped}",
                f"- **Errors:** ⚠️ {errors}",
                ""
            ])
        
        # Next steps
        lines.extend([
            "## Post-Migration Checklist",
            "",
            "### Immediate Actions:",
            "- [ ] Review validation results and investigate any failures",
            "- [ ] Test application connectivity to Snowflake",
            "- [ ] Verify user permissions and roles",
            "- [ ] Test critical queries and reports",
            "",
            "### Data Quality:",
            "- [ ] Run additional business-specific validation queries",
            "- [ ] Compare sample data between PostgreSQL and Snowflake",
            "- [ ] Verify foreign key relationships (documented but not enforced)",
            "",
            "### Performance:",
            "- [ ] Analyze query performance on large tables",
            "- [ ] Review and optimize cluster keys if needed",
            "- [ ] Set up warehouse auto-suspend and auto-resume",
            "",
            "### Security & Governance:",
            "- [ ] Implement row-level security if needed",
            "- [ ] Set up data masking policies for PII",
            "- [ ] Configure role-based access control (RBAC)",
            "- [ ] Enable data governance features (tags, lineage)",
            "",
            "### Operations:",
            "- [ ] Set up monitoring and alerting",
            "- [ ] Document connection strings and credentials",
            "- [ ] Plan for ongoing data synchronization (if needed)",
            "- [ ] Clean up staging files from internal stage",
            "",
            "### Application Cutover:",
            "- [ ] Update application configuration to point to Snowflake",
            "- [ ] Test application in staging environment",
            "- [ ] Plan production cutover window",
            "- [ ] Prepare rollback plan",
            ""
        ])
        
        # Unresolved issues
        if failed_tables > 0:
            lines.extend([
                "## ⚠️ Unresolved Issues",
                "",
                f"**{failed_tables} table(s) failed to migrate.** Review the error messages above and:",
                "",
                "1. Check PostgreSQL connection and permissions",
                "2. Verify Snowflake warehouse is running",
                "3. Check for data type incompatibilities",
                "4. Review Snowflake stage and file format configuration",
                "5. Check disk space in temp directory",
                "",
                "Re-run the migration with the same `run_id` to resume from the failed tables.",
                ""
            ])
        
        return "\n".join(lines)
