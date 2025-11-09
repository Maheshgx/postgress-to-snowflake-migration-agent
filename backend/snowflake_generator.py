"""
Snowflake schema generator and type mapper.
Generates optimized Snowflake DDL from PostgreSQL analysis.
"""
from typing import Dict, List, Any, Optional, Tuple
import yaml
from backend.models import MigrationPreferences, CaseStyle
from backend.logger import get_logger

logger = get_logger(__name__)


class TypeMapper:
    """Maps PostgreSQL data types to Snowflake equivalents."""
    
    # PostgreSQL to Snowflake type mapping
    TYPE_MAP = {
        # Numeric types
        'smallint': 'NUMBER(5,0)',
        'integer': 'NUMBER(10,0)',
        'bigint': 'NUMBER(19,0)',
        'decimal': 'NUMBER',
        'numeric': 'NUMBER',
        'real': 'FLOAT',
        'double precision': 'FLOAT',
        'smallserial': 'NUMBER(5,0)',
        'serial': 'NUMBER(10,0)',
        'bigserial': 'NUMBER(19,0)',
        'money': 'NUMBER(19,4)',
        
        # Character types
        'character varying': 'VARCHAR',
        'varchar': 'VARCHAR',
        'character': 'CHAR',
        'char': 'CHAR',
        'text': 'VARCHAR',
        
        # Binary types
        'bytea': 'BINARY',
        
        # Date/Time types
        'timestamp without time zone': 'TIMESTAMP_NTZ',
        'timestamp with time zone': 'TIMESTAMP_TZ',
        'timestamp': 'TIMESTAMP_NTZ',
        'timestamptz': 'TIMESTAMP_TZ',
        'date': 'DATE',
        'time without time zone': 'TIME',
        'time with time zone': 'TIME',
        'time': 'TIME',
        'interval': 'VARCHAR',  # No direct equivalent
        
        # Boolean
        'boolean': 'BOOLEAN',
        'bool': 'BOOLEAN',
        
        # Semi-structured
        'json': 'VARIANT',
        'jsonb': 'VARIANT',
        
        # UUID
        'uuid': 'VARCHAR(36)',
        
        # Network types
        'inet': 'VARCHAR(45)',
        'cidr': 'VARCHAR(45)',
        'macaddr': 'VARCHAR(17)',
        
        # Geometric types (store as text)
        'point': 'VARCHAR',
        'line': 'VARCHAR',
        'lseg': 'VARCHAR',
        'box': 'VARCHAR',
        'path': 'VARCHAR',
        'polygon': 'VARCHAR',
        'circle': 'VARCHAR',
        
        # Arrays (store as VARIANT)
        'ARRAY': 'VARIANT',
        
        # User-defined (enums, composites)
        'USER-DEFINED': 'VARCHAR',
    }
    
    @classmethod
    def map_type(cls, pg_type: str, udt_name: str = None, 
                 char_max_length: int = None, numeric_precision: int = None,
                 numeric_scale: int = None) -> Tuple[str, str]:
        """
        Map PostgreSQL type to Snowflake type.
        Returns (snowflake_type, rationale).
        """
        pg_type_lower = pg_type.lower()
        
        # Handle array types
        if '[]' in pg_type or pg_type == 'ARRAY':
            return 'VARIANT', 'PostgreSQL array mapped to VARIANT for semi-structured storage'
        
        # Handle numeric with precision/scale
        if pg_type_lower in ('numeric', 'decimal'):
            if numeric_precision and numeric_scale is not None:
                sf_type = f'NUMBER({numeric_precision},{numeric_scale})'
            elif numeric_precision:
                sf_type = f'NUMBER({numeric_precision},0)'
            else:
                sf_type = 'NUMBER(38,0)'
            return sf_type, f'PostgreSQL {pg_type} with precision/scale preserved'
        
        # Handle VARCHAR with length
        if pg_type_lower in ('character varying', 'varchar', 'character', 'char'):
            if char_max_length:
                if char_max_length > 16777216:  # Snowflake max VARCHAR
                    sf_type = 'VARCHAR'
                    rationale = f'PostgreSQL {pg_type}({char_max_length}) exceeds Snowflake max; using VARCHAR(16777216)'
                else:
                    sf_type = f'VARCHAR({char_max_length})'
                    rationale = f'PostgreSQL {pg_type} with length preserved'
            else:
                sf_type = 'VARCHAR'
                rationale = f'PostgreSQL {pg_type} mapped to VARCHAR'
            return sf_type, rationale
        
        # Handle text
        if pg_type_lower == 'text':
            return 'VARCHAR', 'PostgreSQL TEXT mapped to VARCHAR (unlimited)'
        
        # Look up in type map
        if pg_type_lower in cls.TYPE_MAP:
            sf_type = cls.TYPE_MAP[pg_type_lower]
            return sf_type, f'Standard mapping: {pg_type} → {sf_type}'
        
        # Handle user-defined types (enums, etc.)
        if pg_type == 'USER-DEFINED':
            return 'VARCHAR', f'User-defined type ({udt_name}) mapped to VARCHAR; consider adding validation'
        
        # Default fallback
        logger.warning(f"Unknown PostgreSQL type: {pg_type}, defaulting to VARCHAR")
        return 'VARCHAR', f'Unknown type {pg_type} mapped to VARCHAR (needs review)'


class SnowflakeGenerator:
    """Generates Snowflake DDL and migration artifacts."""
    
    def __init__(self, analysis: Dict[str, Any], preferences: MigrationPreferences):
        self.analysis = analysis
        self.preferences = preferences
        self.mapping_decisions = []
        self.ddl_statements = []
        self.improvement_recommendations = []
    
    def normalize_identifier(self, name: str) -> str:
        """Normalize identifier based on case_style preference."""
        if self.preferences.case_style == CaseStyle.UPPER:
            return name.upper()
        elif self.preferences.case_style == CaseStyle.LOWER:
            return name.lower()
        else:  # PRESERVE
            return name
    
    def quote_identifier(self, name: str) -> str:
        """Quote identifier if needed."""
        normalized = self.normalize_identifier(name)
        
        # Check if quoting is needed
        snowflake_reserved = {'ACCOUNT', 'ALL', 'ALTER', 'AND', 'ANY', 'AS', 'BETWEEN', 
                              'BY', 'CASE', 'CAST', 'CHECK', 'COLUMN', 'CONNECT', 'COPY',
                              'CREATE', 'CURRENT', 'DATABASE', 'DELETE', 'DISTINCT', 'DROP'}
        
        if normalized.upper() in snowflake_reserved or not normalized.replace('_', '').isalnum():
            return f'"{normalized}"'
        return normalized
    
    def generate_database_ddl(self, database_name: str) -> List[str]:
        """Generate database-level DDL."""
        db_name = self.quote_identifier(database_name)
        
        statements = [
            f"-- Database: {db_name}",
            f"CREATE DATABASE IF NOT EXISTS {db_name};",
            f"USE DATABASE {db_name};",
            ""
        ]
        
        return statements
    
    def generate_schema_ddl(self, schema_name: str) -> List[str]:
        """Generate schema DDL."""
        schema = self.quote_identifier(schema_name)
        
        statements = [
            f"-- Schema: {schema}",
            f"CREATE SCHEMA IF NOT EXISTS {schema};",
            ""
        ]
        
        return statements
    
    def generate_sequence_ddl(self, schema_name: str, sequence: Dict[str, Any]) -> str:
        """Generate sequence DDL."""
        schema = self.quote_identifier(schema_name)
        seq_name = self.quote_identifier(sequence['sequence_name'])
        
        start = sequence['start_value'] or 1
        increment = sequence['increment'] or 1
        
        ddl = f"CREATE SEQUENCE IF NOT EXISTS {schema}.{seq_name} START = {start} INCREMENT = {increment};"
        return ddl
    
    def generate_table_ddl(self, schema_name: str, table_detail: Dict[str, Any]) -> Tuple[str, List[Dict]]:
        """
        Generate table DDL and return mapping decisions.
        Returns (ddl_string, column_mappings).
        """
        table_name = table_detail['table_name']
        table_metadata = table_detail['table_metadata']
        columns = table_detail['columns']
        constraints = table_detail['constraints']
        
        schema = self.quote_identifier(schema_name)
        table = self.quote_identifier(table_name)
        full_table_name = f"{schema}.{table}"
        
        column_defs = []
        column_mappings = []
        
        # Generate column definitions
        for col in columns:
            col_name = self.quote_identifier(col['column_name'])
            
            # Map type
            sf_type, rationale = TypeMapper.map_type(
                col['data_type'],
                col['udt_name'],
                col['character_maximum_length'],
                col['numeric_precision'],
                col['numeric_scale']
            )
            
            # Build column definition
            col_def = f"    {col_name} {sf_type}"
            
            # Handle identity columns
            if col['is_identity'] == 'YES' and self.preferences.use_identity_for_serial:
                start = col['identity_start'] or 1
                increment = col['identity_increment'] or 1
                col_def += f" IDENTITY({start}, {increment})"
            elif col['serial_sequence']:
                # Serial column without IDENTITY - will need sequence + default
                seq_name = col['serial_sequence'].split('.')[-1]
                col_def += f" DEFAULT {schema}.{self.quote_identifier(seq_name)}.NEXTVAL"
            elif col['column_default']:
                # Handle other defaults
                default_val = col['column_default']
                # Clean up PostgreSQL-specific syntax
                if default_val.startswith('nextval('):
                    # Extract sequence name
                    seq_match = default_val.split("'")[1] if "'" in default_val else None
                    if seq_match:
                        seq_name = seq_match.split('.')[-1]
                        col_def += f" DEFAULT {schema}.{self.quote_identifier(seq_name)}.NEXTVAL"
                elif not default_val.lower().startswith('nextval'):
                    # Keep other defaults, but may need transformation
                    col_def += f" DEFAULT {default_val}"
            
            # NOT NULL constraint
            if col['is_nullable'] == 'NO':
                col_def += " NOT NULL"
            
            # Add comment if exists
            if col['column_comment']:
                comment = col['column_comment'].replace("'", "''")
                col_def += f" COMMENT '{comment}'"
            
            column_defs.append(col_def)
            
            # Record mapping decision
            column_mappings.append({
                'schema': schema_name,
                'table': table_name,
                'column': col['column_name'],
                'postgres_type': col['data_type'],
                'snowflake_type': sf_type,
                'rationale': rationale,
                'nullable': col['is_nullable'] == 'YES',
                'has_default': col['column_default'] is not None,
                'is_identity': col['is_identity'] == 'YES'
            })
        
        # Build table DDL
        ddl = f"CREATE TABLE IF NOT EXISTS {full_table_name} (\n"
        ddl += ",\n".join(column_defs)
        
        # Add primary key constraint
        if constraints['primary_keys']:
            pk = constraints['primary_keys'][0]
            pk_cols = ', '.join([self.quote_identifier(c) for c in pk['columns']])
            ddl += f",\n    CONSTRAINT {self.quote_identifier(pk['constraint_name'])} PRIMARY KEY ({pk_cols})"
        
        # Add unique constraints
        for uk in constraints['unique_keys']:
            uk_cols = ', '.join([self.quote_identifier(c) for c in uk['columns']])
            ddl += f",\n    CONSTRAINT {self.quote_identifier(uk['constraint_name'])} UNIQUE ({uk_cols})"
        
        ddl += "\n)"
        
        # Add cluster key if specified
        cluster_hint = self.preferences.cluster_key_hints.get(table_name)
        if cluster_hint:
            cluster_cols = ', '.join([self.quote_identifier(c) for c in cluster_hint])
            ddl += f"\nCLUSTER BY ({cluster_cols})"
        elif table_metadata.get('total_size_bytes', 0) > 10 * 1024 * 1024 * 1024:  # > 10GB
            # Suggest cluster key for very large tables
            self.improvement_recommendations.append({
                'type': 'CLUSTER_KEY',
                'table': full_table_name,
                'recommendation': f'Table {full_table_name} is very large ({table_metadata["total_size_bytes"]/(1024**3):.2f} GB). '
                                  'Consider adding a CLUSTER KEY on frequently filtered columns (e.g., date/timestamp columns) '
                                  'to improve query performance.'
            })
        
        ddl += ";"
        
        # Add table comment
        if table_metadata.get('table_comment'):
            comment = table_metadata['table_comment'].replace("'", "''")
            ddl += f"\nCOMMENT ON TABLE {full_table_name} IS '{comment}';"
        
        # Add foreign key constraints as comments (not enforced in Snowflake standard tables)
        if constraints['foreign_keys']:
            ddl += f"\n\n-- Foreign key constraints (for documentation; not enforced on standard tables):"
            for fk in constraints['foreign_keys']:
                fk_table = f"{self.quote_identifier(fk['foreign_table_schema'])}.{self.quote_identifier(fk['foreign_table_name'])}"
                ddl += f"\n-- {self.quote_identifier(fk['constraint_name'])}: {col_name} REFERENCES {fk_table}({self.quote_identifier(fk['foreign_column_name'])})"
        
        return ddl, column_mappings
    
    def generate_view_ddl(self, schema_name: str, view: Dict[str, Any]) -> str:
        """Generate view DDL (requires transformation of PostgreSQL-specific syntax)."""
        schema = self.quote_identifier(schema_name)
        view_name = self.quote_identifier(view['view_name'])
        
        # Note: View definition transformation is complex and may require manual review
        view_def = view['view_definition']
        
        ddl = f"-- View: {schema}.{view_name}\n"
        ddl += f"-- Original PostgreSQL definition:\n"
        ddl += f"-- {view_def}\n"
        ddl += f"-- TODO: Review and transform PostgreSQL-specific syntax for Snowflake\n"
        ddl += f"-- CREATE OR REPLACE VIEW {schema}.{view_name} AS\n"
        ddl += f"-- <transformed_query>;\n"
        
        return ddl
    
    def generate_stage_and_format(self, stage_name: str, file_format_name: str) -> List[str]:
        """Generate stage and file format DDL."""
        stage = self.quote_identifier(stage_name)
        file_format = self.quote_identifier(file_format_name)
        
        statements = [
            "-- Internal stage for data loading",
            f"CREATE STAGE IF NOT EXISTS {stage};",
            ""
        ]
        
        if self.preferences.format == 'CSV':
            statements.extend([
                "-- File format for CSV",
                f"CREATE FILE FORMAT IF NOT EXISTS {file_format}",
                "    TYPE = 'CSV'",
                "    COMPRESSION = 'GZIP'",
                "    FIELD_DELIMITER = ','",
                "    RECORD_DELIMITER = '\\n'",
                "    SKIP_HEADER = 1",
                "    FIELD_OPTIONALLY_ENCLOSED_BY = '\"'",
                "    TRIM_SPACE = TRUE",
                "    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE",
                "    ESCAPE = 'NONE'",
                "    ESCAPE_UNENCLOSED_FIELD = '\\\\'",
                "    DATE_FORMAT = 'AUTO'",
                "    TIMESTAMP_FORMAT = 'AUTO'",
                "    NULL_IF = ('\\\\N', 'NULL', 'null', '');",
                ""
            ])
        else:  # PARQUET
            statements.extend([
                "-- File format for Parquet",
                f"CREATE FILE FORMAT IF NOT EXISTS {file_format}",
                "    TYPE = 'PARQUET'",
                "    COMPRESSION = 'SNAPPY';",
                ""
            ])
        
        return statements
    
    def generate_complete_ddl(self, snowflake_config: Dict[str, str]) -> str:
        """Generate complete Snowflake DDL script."""
        logger.info("Generating Snowflake DDL")
        
        ddl_lines = [
            "-- =============================================================================",
            "-- Snowflake Migration DDL",
            f"-- Generated: {self.analysis['metadata']['analysis_timestamp']}",
            f"-- Source: PostgreSQL {self.analysis['metadata']['database']}",
            "-- =============================================================================",
            ""
        ]
        
        # Database DDL
        ddl_lines.extend(self.generate_database_ddl(snowflake_config['database']))
        
        # Stage and file format
        ddl_lines.extend(self.generate_stage_and_format(
            snowflake_config['stage'],
            snowflake_config['file_format']
        ))
        
        # Process each schema
        for schema_detail in self.analysis['schemas']:
            schema_name = schema_detail['schema_name']
            
            # Schema DDL
            ddl_lines.extend(self.generate_schema_ddl(schema_name))
            
            # Sequences
            for sequence in schema_detail['sequences']:
                ddl_lines.append(self.generate_sequence_ddl(schema_name, sequence))
            ddl_lines.append("")
            
            # Tables
            for table_detail in schema_detail['tables']:
                table_ddl, column_mappings = self.generate_table_ddl(schema_name, table_detail)
                ddl_lines.append(table_ddl)
                ddl_lines.append("")
                self.mapping_decisions.extend(column_mappings)
            
            # Views (with warnings)
            for view in schema_detail['views']:
                ddl_lines.append(self.generate_view_ddl(schema_name, view))
                ddl_lines.append("")
        
        return "\n".join(ddl_lines)
    
    def generate_mapping_decisions_yaml(self) -> str:
        """Generate YAML file with type mapping decisions."""
        mapping_yaml = {
            'metadata': {
                'generated': self.analysis['metadata']['analysis_timestamp'],
                'source_database': self.analysis['metadata']['database'],
                'case_style': self.preferences.case_style.value
            },
            'mappings': self.mapping_decisions
        }
        
        return yaml.dump(mapping_yaml, sort_keys=False, default_flow_style=False)
    
    def generate_improvement_recommendations(self) -> str:
        """Generate improvement recommendations document."""
        lines = [
            "# Snowflake Migration - Improvement Recommendations",
            "",
            f"**Generated:** {self.analysis['metadata']['analysis_timestamp']}",
            f"**Source Database:** {self.analysis['metadata']['database']}",
            "",
            "---",
            ""
        ]
        
        # Warehouse sizing recommendation
        total_size_gb = self.analysis['volumetrics']['total_size_gb']
        lines.extend([
            "## 1. Warehouse Sizing & Cost Optimization",
            "",
            f"**Total Data Volume:** ~{total_size_gb} GB",
            "",
            "### Recommended Warehouse Configuration:",
            ""
        ])
        
        if total_size_gb < 10:
            wh_size = "X-SMALL to SMALL"
        elif total_size_gb < 100:
            wh_size = "SMALL to MEDIUM"
        elif total_size_gb < 500:
            wh_size = "MEDIUM to LARGE"
        else:
            wh_size = "LARGE to X-LARGE"
        
        lines.extend([
            f"- **Initial Load:** Use {wh_size} warehouse",
            "- **Auto-Suspend:** Set to 60 seconds for development, 300 seconds for production",
            "- **Auto-Resume:** Enable",
            "- **Multi-Cluster:** Consider for high concurrency workloads",
            "",
            "### Cost Optimization Tips:",
            "- Use separate warehouses for ETL vs analytical queries",
            "- Enable query result caching",
            "- Set resource monitors to prevent runaway costs",
            "- Review and optimize expensive queries",
            ""
        ])
        
        # Cluster key recommendations
        if self.improvement_recommendations:
            lines.extend([
                "## 2. Performance Optimizations",
                "",
                "### Cluster Key Candidates:",
                ""
            ])
            
            for rec in self.improvement_recommendations:
                if rec['type'] == 'CLUSTER_KEY':
                    lines.append(f"- **{rec['table']}:** {rec['recommendation']}")
                    lines.append("")
        
        # Semi-structured data recommendations
        has_json = False
        for schema_detail in self.analysis['schemas']:
            if schema_detail['special_types']['summary'].get('JSON'):
                has_json = True
                break
        
        if has_json:
            lines.extend([
                "## 3. Semi-Structured Data (JSON/VARIANT)",
                "",
                "JSON/JSONB columns have been mapped to VARIANT type. Consider:",
                "",
                "- Create projection views for frequently accessed JSON paths",
                "- Use `FLATTEN()` for array processing",
                "- Consider extracting stable fields to typed columns for better performance",
                "- Enable automatic clustering on frequently queried VARIANT columns",
                ""
            ])
        
        # Constraints and data quality
        lines.extend([
            "## 4. Constraints & Data Quality",
            "",
            "Primary Keys (PK) and Unique Keys (UK) are created but NOT ENFORCED on standard Snowflake tables.",
            "Foreign Keys (FK) are documented but not enforced.",
            "",
            "**Recommendations:**",
            "- Implement data quality checks in your ETL pipeline",
            "- Use Snowflake's Data Quality functions (EQUAL, NOT_NULL, etc.) in dbt or similar tools",
            "- Consider creating validation views or tasks",
            "- For enforced constraints, evaluate Snowflake Hybrid Tables (preview feature)",
            ""
        ])
        
        # Trigger and function migration
        has_triggers = any(
            len(table['triggers']) > 0 
            for schema in self.analysis['schemas'] 
            for table in schema['tables']
        )
        
        has_functions = any(
            len(schema['functions']) > 0 
            for schema in self.analysis['schemas']
        )
        
        if has_triggers or has_functions:
            lines.extend([
                "## 5. Triggers & Functions Migration",
                ""
            ])
            
            if has_triggers:
                lines.extend([
                    "### Triggers:",
                    "PostgreSQL triggers are not directly portable to Snowflake. Consider:",
                    "- Use Snowflake Streams to capture change data",
                    "- Use Snowflake Tasks for scheduled processing",
                    "- Implement trigger logic in your application or ETL layer",
                    ""
                ])
            
            if has_functions:
                lines.extend([
                    "### Functions & Stored Procedures:",
                    "PostgreSQL functions require manual conversion:",
                    "- Review PL/pgSQL syntax and convert to Snowflake's JavaScript or SQL procedures",
                    "- Many PostgreSQL functions have Snowflake equivalents",
                    "- Consider UDFs (User Defined Functions) for custom logic",
                    ""
                ])
        
        # Security and governance
        lines.extend([
            "## 6. Security & Governance",
            "",
            "### Role-Based Access Control (RBAC):",
            "Create roles for different access levels:",
            "",
            "```sql",
            "-- Reader role",
            "CREATE ROLE IF NOT EXISTS DATA_READER;",
            "GRANT USAGE ON DATABASE <database> TO ROLE DATA_READER;",
            "GRANT USAGE ON ALL SCHEMAS IN DATABASE <database> TO ROLE DATA_READER;",
            "GRANT SELECT ON ALL TABLES IN DATABASE <database> TO ROLE DATA_READER;",
            "",
            "-- Writer role",
            "CREATE ROLE IF NOT EXISTS DATA_WRITER;",
            "GRANT USAGE ON DATABASE <database> TO ROLE DATA_WRITER;",
            "GRANT USAGE ON ALL SCHEMAS IN DATABASE <database> TO ROLE DATA_WRITER;",
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN DATABASE <database> TO ROLE DATA_WRITER;",
            "",
            "-- Admin role",
            "CREATE ROLE IF NOT EXISTS DATA_ADMIN;",
            "GRANT ALL ON DATABASE <database> TO ROLE DATA_ADMIN;",
            "```",
            "",
            "### Data Masking:",
            "Review tables for sensitive data (PII) and implement masking policies:",
            "- Email addresses",
            "- Social Security Numbers",
            "- Credit card numbers",
            "- Phone numbers",
            "",
            "### Row-Level Security:",
            "Consider implementing row-level security for multi-tenant data.",
            ""
        ])
        
        # Monitoring and observability
        lines.extend([
            "## 7. Monitoring & Observability",
            "",
            "Set up monitoring for:",
            "- Query performance (slow queries, expensive queries)",
            "- Warehouse utilization and costs",
            "- Data pipeline failures",
            "- Storage growth",
            "",
            "**Tools:**",
            "- Snowflake's Query History & Account Usage views",
            "- Resource Monitors for cost control",
            "- Third-party monitoring tools (Datadog, New Relic, etc.)",
            ""
        ])
        
        return "\n".join(lines)
