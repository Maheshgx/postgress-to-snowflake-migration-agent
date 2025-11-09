"""
Main migration orchestrator.
Coordinates analysis, planning, execution, and validation phases.
"""
import json
import yaml
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid
from backend.models import MigrationRequest, MigrationStatus, MigrationProgress, TableStatus
from backend.postgres_analyzer import PostgresAnalyzer
from backend.snowflake_generator import SnowflakeGenerator
from backend.data_pipeline import MigrationPipeline
from backend.validation import DataValidator, ReportGenerator
from backend.logger import get_logger
from backend.config import settings

logger = get_logger(__name__)


class MigrationOrchestrator:
    """Orchestrates the complete migration workflow."""
    
    def __init__(self, request: MigrationRequest):
        self.request = request
        self.run_id = request.control.run_id or str(uuid.uuid4())
        self.artifacts_dir = os.path.join(settings.artifacts_path, self.run_id)
        self.temp_dir = os.path.join(settings.temp_path, self.run_id)
        
        # Create directories
        os.makedirs(self.artifacts_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.status = MigrationStatus.PENDING
        self.analysis_results = None
        self.migration_results = []
        self.validation_results = []
        self.log_entries = []
    
    def log(self, level: str, category: str, message: str, **kwargs):
        """Add structured log entry."""
        entry = {
            'ts': datetime.utcnow().isoformat(),
            'run_id': self.run_id,
            'level': level,
            'category': category,
            'message': message,
            **kwargs
        }
        self.log_entries.append(entry)
        
        # Also log to structured logger
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(message, **kwargs)
    
    def save_log(self):
        """Save log entries to NDJSON file."""
        log_file = os.path.join(self.artifacts_dir, 'run_log.ndjson')
        with open(log_file, 'w') as f:
            for entry in self.log_entries:
                f.write(json.dumps(entry, default=str) + '\n')
        logger.info(f"Log saved to {log_file}")
    
    def get_progress(self) -> MigrationProgress:
        """Get current migration progress."""
        total_tables = 0
        completed_tables = 0
        
        if self.analysis_results:
            for schema in self.analysis_results['schemas']:
                total_tables += len(schema['tables'])
        
        completed_tables = len([r for r in self.migration_results if r.get('status') == 'completed'])
        
        progress_percent = 0
        if total_tables > 0:
            if self.status == MigrationStatus.ANALYZING:
                progress_percent = 10
            elif self.status == MigrationStatus.PLANNING:
                progress_percent = 20
            elif self.status == MigrationStatus.AWAITING_CONFIRMATION:
                progress_percent = 25
            elif self.status == MigrationStatus.EXECUTING:
                progress_percent = 30 + (completed_tables / total_tables * 60)
            elif self.status == MigrationStatus.VALIDATING:
                progress_percent = 90
            elif self.status == MigrationStatus.COMPLETED:
                progress_percent = 100
        
        table_statuses = []
        for result in self.migration_results:
            table_statuses.append(TableStatus(
                table_name=result.get('table', 'unknown'),
                schema_name=result.get('schema', 'unknown'),
                status=result.get('status', 'unknown'),
                rows_loaded=result.get('rows_loaded'),
                bytes_processed=result.get('bytes_processed'),
                duration_ms=result.get('duration_ms'),
                retries=result.get('retries', 0),
                error=result.get('error')
            ))
        
        return MigrationProgress(
            run_id=self.run_id,
            status=self.status,
            phase=self.status.value,
            progress_percent=progress_percent,
            tables_completed=completed_tables,
            tables_total=total_tables,
            table_statuses=table_statuses
        )
    
    def analyze(self) -> Dict[str, Any]:
        """Phase 1: Analyze PostgreSQL database."""
        self.log('INFO', 'analyze', 'Starting PostgreSQL analysis')
        self.status = MigrationStatus.ANALYZING
        
        try:
            analyzer = PostgresAnalyzer(self.request.postgres)
            self.analysis_results = analyzer.analyze_complete()
            
            # Save analysis report
            analysis_file = os.path.join(self.artifacts_dir, 'analysis_report.json')
            analyzer.save_analysis(analysis_file)
            
            self.log('INFO', 'analyze', 'PostgreSQL analysis completed',
                    schemas=len(self.analysis_results['schemas']),
                    total_tables=sum(len(s['tables']) for s in self.analysis_results['schemas']))
            
            return self.analysis_results
        
        except Exception as e:
            self.log('ERROR', 'analyze', f'Analysis failed: {str(e)}')
            self.status = MigrationStatus.FAILED
            raise
    
    def plan(self) -> Dict[str, List[str]]:
        """Phase 2: Generate migration plan and artifacts."""
        self.log('INFO', 'plan', 'Generating migration plan')
        self.status = MigrationStatus.PLANNING
        
        try:
            if not self.analysis_results:
                raise ValueError("Analysis results not available. Run analyze() first.")
            
            generator = SnowflakeGenerator(self.analysis_results, self.request.preferences)
            
            # Generate Snowflake DDL
            snowflake_config = {
                'database': self.request.snowflake.database,
                'stage': self.request.snowflake.stage,
                'file_format': self.request.snowflake.file_format
            }
            
            ddl = generator.generate_complete_ddl(snowflake_config)
            ddl_file = os.path.join(self.artifacts_dir, 'snowflake_objects.sql')
            with open(ddl_file, 'w') as f:
                f.write(ddl)
            
            # Generate mapping decisions
            mapping_yaml = generator.generate_mapping_decisions_yaml()
            mapping_file = os.path.join(self.artifacts_dir, 'mapping_decisions.yml')
            with open(mapping_file, 'w') as f:
                f.write(mapping_yaml)
            
            # Generate improvement recommendations
            recommendations = generator.generate_improvement_recommendations()
            recommendations_file = os.path.join(self.artifacts_dir, 'improvement_recommendations.md')
            with open(recommendations_file, 'w') as f:
                f.write(recommendations)
            
            # Generate load plan
            load_plan = self._generate_load_plan()
            load_plan_file = os.path.join(self.artifacts_dir, 'load_plan.yml')
            with open(load_plan_file, 'w') as f:
                yaml.dump(load_plan, f, sort_keys=False)
            
            # Generate validation SQL
            validator = DataValidator(self.request.postgres, self.request.snowflake, self.request.auth.access_token)
            validation_sql = validator.generate_validation_sql(self.analysis_results)
            validation_file = os.path.join(self.artifacts_dir, 'post_migration_checks.sql')
            with open(validation_file, 'w') as f:
                f.write(validation_sql)
            
            # Generate sample COPY commands
            copy_commands = self._generate_copy_commands()
            copy_file = os.path.join(self.artifacts_dir, 'copy_commands.sql')
            with open(copy_file, 'w') as f:
                f.write(copy_commands)
            
            artifacts = [
                'analysis_report.json',
                'snowflake_objects.sql',
                'mapping_decisions.yml',
                'improvement_recommendations.md',
                'load_plan.yml',
                'post_migration_checks.sql',
                'copy_commands.sql'
            ]
            
            self.log('INFO', 'plan', 'Migration plan generated', artifacts=artifacts)
            self.status = MigrationStatus.AWAITING_CONFIRMATION
            
            return {'artifacts': artifacts}
        
        except Exception as e:
            self.log('ERROR', 'plan', f'Planning failed: {str(e)}')
            self.status = MigrationStatus.FAILED
            raise
    
    def _generate_load_plan(self) -> Dict[str, Any]:
        """Generate detailed load plan."""
        plan = {
            'metadata': {
                'run_id': self.run_id,
                'generated': datetime.utcnow().isoformat(),
                'parallelism': self.request.preferences.parallelism,
                'format': self.request.preferences.format.value,
                'max_chunk_mb': self.request.preferences.max_chunk_mb
            },
            'schemas': []
        }
        
        for schema_detail in self.analysis_results['schemas']:
            schema_name = schema_detail['schema_name']
            schema_plan = {
                'schema_name': schema_name,
                'tables': []
            }
            
            for table_detail in schema_detail['tables']:
                table_name = table_detail['table_name']
                table_metadata = table_detail['table_metadata']
                columns = table_detail['columns']
                
                table_plan = {
                    'table_name': table_name,
                    'estimated_rows': table_metadata.get('approximate_row_count', 0),
                    'estimated_size_gb': round(table_metadata.get('total_size_bytes', 0) / (1024**3), 3),
                    'columns': [col['column_name'] for col in columns],
                    'column_count': len(columns),
                    'extract_strategy': 'streaming',
                    'load_strategy': 'bulk_copy',
                    'priority': 'high' if table_metadata.get('total_size_bytes', 0) > 1_000_000_000 else 'normal'
                }
                
                schema_plan['tables'].append(table_plan)
            
            plan['schemas'].append(schema_plan)
        
        return plan
    
    def _generate_copy_commands(self) -> str:
        """Generate sample COPY INTO commands."""
        lines = [
            "-- =============================================================================",
            "-- Sample COPY INTO Commands",
            f"-- Generated: {datetime.utcnow().isoformat()}",
            "-- =============================================================================",
            "",
            "-- These are representative COPY INTO commands.",
            "-- The actual migration will generate specific commands for each data file.",
            ""
        ]
        
        for schema_detail in self.analysis_results['schemas'][:1]:  # Just first schema as example
            schema_name = schema_detail['schema_name']
            
            for table_detail in schema_detail['tables'][:3]:  # First 3 tables as examples
                table_name = table_detail['table_name']
                columns = [col['column_name'] for col in table_detail['columns']]
                
                column_list = ', '.join([f'"{col}"' for col in columns])
                
                lines.extend([
                    f"-- Table: {schema_name}.{table_name}",
                    f"COPY INTO \"{schema_name}\".\"{table_name}\" ({column_list})",
                    f"FROM @{self.request.snowflake.stage}",
                    f"FILES = ('{schema_name}_{table_name}_chunk_0001.csv.gz')",
                    f"FILE_FORMAT = {self.request.snowflake.file_format}",
                    "MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE",
                    "ON_ERROR = 'ABORT_STATEMENT'",
                    "PURGE = FALSE;",
                    ""
                ])
        
        return "\n".join(lines)
    
    def execute(self) -> List[Dict[str, Any]]:
        """Phase 3: Execute migration (only after confirmation)."""
        if not self.request.control.confirm:
            raise ValueError("Migration execution requires explicit confirmation (confirm=true)")
        
        self.log('INFO', 'execute', 'Starting migration execution')
        self.status = MigrationStatus.EXECUTING
        
        try:
            if not self.analysis_results:
                raise ValueError("Analysis results not available. Run analyze() first.")
            
            # Create Snowflake objects
            self._execute_ddl()
            
            # Migrate data
            pipeline = MigrationPipeline(
                self.request.postgres,
                self.request.snowflake,
                self.request.auth.access_token,
                self.request.preferences,
                self.temp_dir
            )
            
            for schema_detail in self.analysis_results['schemas']:
                schema_name = schema_detail['schema_name']
                tables = schema_detail['tables']
                
                self.log('INFO', 'execute', f'Migrating schema: {schema_name}', table_count=len(tables))
                
                schema_results = pipeline.migrate_schema(schema_name, tables)
                self.migration_results.extend(schema_results)
            
            self.log('INFO', 'execute', 'Migration execution completed',
                    total_tables=len(self.migration_results),
                    successful=len([r for r in self.migration_results if r.get('status') == 'completed']))
            
            return self.migration_results
        
        except Exception as e:
            self.log('ERROR', 'execute', f'Execution failed: {str(e)}')
            self.status = MigrationStatus.FAILED
            raise
    
    def _execute_ddl(self):
        """Execute Snowflake DDL statements."""
        self.log('INFO', 'ddl', 'Executing Snowflake DDL')
        
        try:
            from backend.data_pipeline import SnowflakeLoader
            
            loader = SnowflakeLoader(
                self.request.snowflake,
                self.request.auth.access_token,
                self.request.preferences
            )
            
            loader.connect()
            
            # Read and execute DDL script
            ddl_file = os.path.join(self.artifacts_dir, 'snowflake_objects.sql')
            with open(ddl_file, 'r') as f:
                ddl_script = f.read()
            
            loader.execute_ddl_script(ddl_script)
            loader.disconnect()
            
            self.log('INFO', 'ddl', 'DDL execution completed')
        
        except Exception as e:
            self.log('ERROR', 'ddl', f'DDL execution failed: {str(e)}')
            raise
    
    def validate(self) -> List[Dict[str, Any]]:
        """Phase 4: Validate migrated data."""
        self.log('INFO', 'validate', 'Starting data validation')
        self.status = MigrationStatus.VALIDATING
        
        try:
            validator = DataValidator(
                self.request.postgres,
                self.request.snowflake,
                self.request.auth.access_token
            )
            
            validator.connect_postgres()
            validator.connect_snowflake()
            
            # Validate each migrated table
            for schema_detail in self.analysis_results['schemas']:
                schema_name = schema_detail['schema_name']
                
                for table_detail in schema_detail['tables']:
                    table_name = table_detail['table_name']
                    
                    # Only validate successfully migrated tables
                    migrated = any(
                        r.get('schema') == schema_name and 
                        r.get('table') == table_name and 
                        r.get('status') == 'completed'
                        for r in self.migration_results
                    )
                    
                    if migrated:
                        table_validations = validator.validate_table(schema_name, table_name, table_detail)
                        self.validation_results.extend(table_validations)
            
            validator.disconnect()
            
            self.log('INFO', 'validate', 'Validation completed',
                    total_checks=len(self.validation_results),
                    passed=len([r for r in self.validation_results if r.get('status') == 'PASS']))
            
            return self.validation_results
        
        except Exception as e:
            self.log('ERROR', 'validate', f'Validation failed: {str(e)}')
            # Don't fail the entire migration if validation fails
            return self.validation_results
    
    def finalize(self) -> str:
        """Phase 5: Generate final report and cleanup."""
        self.log('INFO', 'finalize', 'Generating final report')
        
        try:
            # Generate summary report
            summary = ReportGenerator.generate_summary_markdown(
                self.run_id,
                self.analysis_results,
                self.migration_results,
                self.validation_results
            )
            
            summary_file = os.path.join(self.artifacts_dir, 'summary.md')
            with open(summary_file, 'w') as f:
                f.write(summary)
            
            # Save log
            self.save_log()
            
            # Update status
            failed_count = len([r for r in self.migration_results if r.get('status') == 'failed'])
            if failed_count == 0:
                self.status = MigrationStatus.COMPLETED
            else:
                self.status = MigrationStatus.FAILED
            
            self.log('INFO', 'finalize', 'Migration finalized', status=self.status.value)
            
            return summary_file
        
        except Exception as e:
            self.log('ERROR', 'finalize', f'Finalization failed: {str(e)}')
            raise
    
    def run_complete(self) -> Dict[str, Any]:
        """Run complete migration workflow."""
        try:
            # Phase 1: Analyze
            self.analyze()
            
            # Phase 2: Plan
            plan_result = self.plan()
            
            # If dry run, stop here
            if self.request.preferences.dry_run:
                self.log('INFO', 'migration', 'Dry run completed - no execution')
                self.status = MigrationStatus.COMPLETED
                self.finalize()
                
                return {
                    'run_id': self.run_id,
                    'status': self.status.value,
                    'message': 'Dry run completed. Review artifacts and re-run with confirm=true to execute.',
                    'artifacts_dir': self.artifacts_dir
                }
            
            # Phase 3: Execute (only if confirmed)
            if self.request.control.confirm:
                self.execute()
                
                # Phase 4: Validate
                self.validate()
            else:
                self.log('INFO', 'migration', 'Awaiting confirmation to execute')
                
                return {
                    'run_id': self.run_id,
                    'status': MigrationStatus.AWAITING_CONFIRMATION.value,
                    'message': 'Plan generated. Review artifacts and re-run with confirm=true to execute migration.',
                    'artifacts_dir': self.artifacts_dir
                }
            
            # Phase 5: Finalize
            self.finalize()
            
            return {
                'run_id': self.run_id,
                'status': self.status.value,
                'message': f'Migration completed with status: {self.status.value}',
                'artifacts_dir': self.artifacts_dir,
                'summary': {
                    'total_tables': len(self.migration_results),
                    'successful': len([r for r in self.migration_results if r.get('status') == 'completed']),
                    'failed': len([r for r in self.migration_results if r.get('status') == 'failed']),
                    'total_rows': sum(r.get('rows_loaded', 0) for r in self.migration_results)
                }
            }
        
        except Exception as e:
            self.status = MigrationStatus.FAILED
            self.log('ERROR', 'migration', f'Migration failed: {str(e)}')
            self.save_log()
            raise
