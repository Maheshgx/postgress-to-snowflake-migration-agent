"""
PostgreSQL database analyzer and introspection module.
Gathers comprehensive metadata about schemas, tables, columns, constraints, indexes, etc.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Any, Optional
import json
from datetime import datetime
from backend.models import PostgresConfig
from backend.logger import get_logger

logger = get_logger(__name__)


class PostgresAnalyzer:
    """Analyzes PostgreSQL database structure and metadata."""
    
    def __init__(self, config: PostgresConfig):
        self.config = config
        self.conn = None
        self.analysis_results = {}
    
    def connect(self) -> bool:
        """Establish connection to PostgreSQL."""
        try:
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
            logger.info(f"Connected to PostgreSQL: {self.config.host}:{self.config.port}/{self.config.database}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise
    
    def disconnect(self):
        """Close PostgreSQL connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Disconnected from PostgreSQL")
    
    def _execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute query and return results as list of dictionaries."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get list of schemas excluding system schemas unless explicitly included."""
        query = """
            SELECT 
                schema_name,
                schema_owner,
                (SELECT COUNT(*) FROM information_schema.tables 
                 WHERE table_schema = s.schema_name) as table_count
            FROM information_schema.schemata s
            WHERE schema_name NOT IN ('pg_toast', 'pg_temp_1', 'pg_toast_temp_1')
            ORDER BY schema_name
        """
        
        schemas = self._execute_query(query)
        
        # Filter based on schema allowlist
        if "*" not in self.config.schemas:
            schemas = [s for s in schemas if s['schema_name'] in self.config.schemas]
        else:
            # Exclude system schemas by default
            schemas = [s for s in schemas if s['schema_name'] not in ('pg_catalog', 'information_schema')]
        
        logger.info(f"Found {len(schemas)} schemas to analyze")
        return schemas
    
    def get_tables(self, schema_name: str) -> List[Dict[str, Any]]:
        """Get all tables in a schema with metadata."""
        query = """
            SELECT 
                t.table_schema,
                t.table_name,
                t.table_type,
                pg_total_relation_size(quote_ident(t.table_schema)||'.'||quote_ident(t.table_name))::bigint as total_size_bytes,
                (SELECT reltuples::bigint FROM pg_class WHERE relname = t.table_name 
                 AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = t.table_schema)) as approximate_row_count,
                obj_description((quote_ident(t.table_schema)||'.'||quote_ident(t.table_name))::regclass::oid) as table_comment
            FROM information_schema.tables t
            WHERE t.table_schema = %s
              AND t.table_type IN ('BASE TABLE', 'VIEW', 'MATERIALIZED VIEW')
            ORDER BY total_size_bytes DESC NULLS LAST, t.table_name
        """
        
        tables = self._execute_query(query, (schema_name,))
        logger.info(f"Found {len(tables)} tables in schema '{schema_name}'")
        return tables
    
    def get_columns(self, schema_name: str, table_name: str) -> List[Dict[str, Any]]:
        """Get all columns for a table with detailed metadata."""
        query = """
            SELECT 
                c.ordinal_position,
                c.column_name,
                c.data_type,
                c.udt_name,
                c.character_maximum_length,
                c.numeric_precision,
                c.numeric_scale,
                c.is_nullable,
                c.column_default,
                c.is_identity,
                c.identity_generation,
                c.identity_start,
                c.identity_increment,
                c.is_generated,
                c.generation_expression,
                col_description((quote_ident(c.table_schema)||'.'||quote_ident(c.table_name))::regclass::oid, c.ordinal_position) as column_comment,
                (SELECT pg_get_serial_sequence(quote_ident(c.table_schema)||'.'||quote_ident(c.table_name), c.column_name)) as serial_sequence
            FROM information_schema.columns c
            WHERE c.table_schema = %s
              AND c.table_name = %s
            ORDER BY c.ordinal_position
        """
        
        columns = self._execute_query(query, (schema_name, table_name))
        return columns
    
    def get_constraints(self, schema_name: str, table_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all constraints (PK, UK, FK, CHECK) for a table."""
        # Primary Keys and Unique Constraints
        pk_uk_query = """
            SELECT 
                tc.constraint_name,
                tc.constraint_type,
                array_agg(kcu.column_name ORDER BY kcu.ordinal_position) as columns
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = %s
              AND tc.table_name = %s
              AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
            GROUP BY tc.constraint_name, tc.constraint_type
        """
        
        # Foreign Keys
        fk_query = """
            SELECT 
                tc.constraint_name,
                kcu.column_name,
                ccu.table_schema AS foreign_table_schema,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.update_rule,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            JOIN information_schema.referential_constraints AS rc
                ON tc.constraint_name = rc.constraint_name
                AND tc.table_schema = rc.constraint_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = %s
              AND tc.table_name = %s
        """
        
        # Check Constraints
        check_query = """
            SELECT 
                cc.constraint_name,
                cc.check_clause
            FROM information_schema.check_constraints cc
            JOIN information_schema.table_constraints tc
                ON cc.constraint_name = tc.constraint_name
            WHERE tc.table_schema = %s
              AND tc.table_name = %s
        """
        
        return {
            'primary_keys': self._execute_query(pk_uk_query.replace("IN ('PRIMARY KEY', 'UNIQUE')", "= 'PRIMARY KEY'"), 
                                                (schema_name, table_name)),
            'unique_keys': self._execute_query(pk_uk_query.replace("IN ('PRIMARY KEY', 'UNIQUE')", "= 'UNIQUE'"), 
                                              (schema_name, table_name)),
            'foreign_keys': self._execute_query(fk_query, (schema_name, table_name)),
            'check_constraints': self._execute_query(check_query, (schema_name, table_name))
        }
    
    def get_indexes(self, schema_name: str, table_name: str) -> List[Dict[str, Any]]:
        """Get all indexes for a table."""
        query = """
            SELECT 
                i.indexname as index_name,
                i.indexdef as index_definition,
                ix.indisunique as is_unique,
                ix.indisprimary as is_primary,
                array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)) as columns,
                pg_size_pretty(pg_relation_size(quote_ident(i.schemaname)||'.'||quote_ident(i.indexname))) as index_size
            FROM pg_indexes i
            JOIN pg_class c ON c.relname = i.tablename
            JOIN pg_index ix ON ix.indexrelid = (quote_ident(i.schemaname)||'.'||quote_ident(i.indexname))::regclass::oid
            JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = ANY(ix.indkey)
            WHERE i.schemaname = %s
              AND i.tablename = %s
            GROUP BY i.indexname, i.indexdef, ix.indisunique, ix.indisprimary, i.schemaname
            ORDER BY i.indexname
        """
        
        indexes = self._execute_query(query, (schema_name, table_name))
        return indexes
    
    def get_sequences(self, schema_name: str) -> List[Dict[str, Any]]:
        """Get all sequences in a schema."""
        query = """
            SELECT 
                sequence_schema,
                sequence_name,
                data_type,
                start_value,
                minimum_value,
                maximum_value,
                increment,
                cycle_option
            FROM information_schema.sequences
            WHERE sequence_schema = %s
            ORDER BY sequence_name
        """
        
        sequences = self._execute_query(query, (schema_name,))
        return sequences
    
    def get_views(self, schema_name: str) -> List[Dict[str, Any]]:
        """Get all views and materialized views in a schema."""
        query = """
            SELECT 
                table_name as view_name,
                view_definition,
                'VIEW' as view_type
            FROM information_schema.views
            WHERE table_schema = %s
            
            UNION ALL
            
            SELECT 
                matviewname as view_name,
                definition as view_definition,
                'MATERIALIZED VIEW' as view_type
            FROM pg_matviews
            WHERE schemaname = %s
            
            ORDER BY view_name
        """
        
        views = self._execute_query(query, (schema_name, schema_name))
        return views
    
    def get_functions(self, schema_name: str) -> List[Dict[str, Any]]:
        """Get all functions and procedures in a schema."""
        query = """
            SELECT 
                r.routine_name as function_name,
                r.routine_type,
                r.data_type as return_type,
                r.routine_definition,
                array_agg(p.parameter_name || ' ' || p.data_type) as parameters
            FROM information_schema.routines r
            LEFT JOIN information_schema.parameters p 
                ON r.specific_name = p.specific_name
            WHERE r.routine_schema = %s
            GROUP BY r.routine_name, r.routine_type, r.data_type, r.routine_definition
            ORDER BY r.routine_name
        """
        
        functions = self._execute_query(query, (schema_name,))
        return functions
    
    def get_triggers(self, schema_name: str, table_name: str) -> List[Dict[str, Any]]:
        """Get all triggers for a table."""
        query = """
            SELECT 
                trigger_name,
                event_manipulation as event,
                action_timing as timing,
                action_statement as action
            FROM information_schema.triggers
            WHERE event_object_schema = %s
              AND event_object_table = %s
            ORDER BY trigger_name
        """
        
        triggers = self._execute_query(query, (schema_name, table_name))
        return triggers
    
    def get_extensions(self) -> List[Dict[str, Any]]:
        """Get installed PostgreSQL extensions."""
        query = """
            SELECT 
                extname as extension_name,
                extversion as version,
                n.nspname as schema
            FROM pg_extension e
            JOIN pg_namespace n ON n.oid = e.extnamespace
            ORDER BY extname
        """
        
        extensions = self._execute_query(query)
        return extensions
    
    def analyze_special_types(self, schema_name: str) -> Dict[str, Any]:
        """Analyze usage of special PostgreSQL types (JSON, arrays, enums, etc.)."""
        query = """
            SELECT 
                c.table_name,
                c.column_name,
                c.data_type,
                c.udt_name,
                CASE 
                    WHEN c.data_type LIKE '%json%' THEN 'JSON'
                    WHEN c.data_type = 'ARRAY' THEN 'ARRAY'
                    WHEN c.data_type = 'USER-DEFINED' THEN 'ENUM/COMPOSITE'
                    WHEN c.data_type = 'bytea' THEN 'BYTEA'
                    WHEN c.data_type = 'uuid' THEN 'UUID'
                    ELSE 'OTHER'
                END as special_type_category
            FROM information_schema.columns c
            WHERE c.table_schema = %s
              AND (c.data_type IN ('json', 'jsonb', 'bytea', 'uuid', 'ARRAY', 'USER-DEFINED')
                   OR c.data_type LIKE '%json%')
            ORDER BY c.table_name, c.column_name
        """
        
        special_types = self._execute_query(query, (schema_name,))
        
        # Group by category
        type_summary = {}
        for col in special_types:
            category = col['special_type_category']
            if category not in type_summary:
                type_summary[category] = []
            type_summary[category].append(f"{col['table_name']}.{col['column_name']}")
        
        return {
            'details': special_types,
            'summary': type_summary
        }
    
    def calculate_volumetrics(self, schemas: List[str]) -> Dict[str, Any]:
        """Calculate database volumetrics and statistics."""
        total_size = 0
        total_tables = 0
        total_rows = 0
        largest_tables = []
        
        for schema_name in schemas:
            tables = self.get_tables(schema_name)
            for table in tables:
                if table['total_size_bytes']:
                    total_size += table['total_size_bytes']
                    total_tables += 1
                    if table['approximate_row_count']:
                        total_rows += table['approximate_row_count']
                    
                    largest_tables.append({
                        'schema': schema_name,
                        'table': table['table_name'],
                        'size_bytes': table['total_size_bytes'],
                        'rows': table['approximate_row_count']
                    })
        
        # Sort and keep top 20
        largest_tables.sort(key=lambda x: x['size_bytes'] or 0, reverse=True)
        largest_tables = largest_tables[:20]
        
        return {
            'total_size_bytes': total_size,
            'total_size_gb': round(total_size / (1024**3), 2),
            'total_tables': total_tables,
            'approximate_total_rows': total_rows,
            'largest_tables': largest_tables
        }
    
    def analyze_complete(self) -> Dict[str, Any]:
        """Perform complete database analysis."""
        logger.info("Starting comprehensive PostgreSQL analysis")
        
        try:
            self.connect()
            
            # Get schemas
            schemas = self.get_schemas()
            schema_names = [s['schema_name'] for s in schemas]
            
            # Analyze each schema
            schema_details = []
            for schema in schemas:
                schema_name = schema['schema_name']
                logger.info(f"Analyzing schema: {schema_name}")
                
                tables = self.get_tables(schema_name)
                sequences = self.get_sequences(schema_name)
                views = self.get_views(schema_name)
                functions = self.get_functions(schema_name)
                special_types = self.analyze_special_types(schema_name)
                
                # Analyze each table
                table_details = []
                for table in tables:
                    if table['table_type'] == 'BASE TABLE':
                        table_name = table['table_name']
                        columns = self.get_columns(schema_name, table_name)
                        constraints = self.get_constraints(schema_name, table_name)
                        indexes = self.get_indexes(schema_name, table_name)
                        triggers = self.get_triggers(schema_name, table_name)
                        
                        table_details.append({
                            'table_name': table_name,
                            'table_metadata': table,
                            'columns': columns,
                            'constraints': constraints,
                            'indexes': indexes,
                            'triggers': triggers
                        })
                
                schema_details.append({
                    'schema_name': schema_name,
                    'schema_metadata': schema,
                    'tables': table_details,
                    'sequences': sequences,
                    'views': views,
                    'functions': functions,
                    'special_types': special_types
                })
            
            # Get extensions
            extensions = self.get_extensions()
            
            # Calculate volumetrics
            volumetrics = self.calculate_volumetrics(schema_names)
            
            # Compile complete analysis
            self.analysis_results = {
                'metadata': {
                    'analysis_timestamp': datetime.utcnow().isoformat(),
                    'database': self.config.database,
                    'host': self.config.host,
                    'schemas_analyzed': len(schema_names)
                },
                'schemas': schema_details,
                'extensions': extensions,
                'volumetrics': volumetrics,
                'compatibility_flags': self._assess_compatibility(schema_details)
            }
            
            logger.info("PostgreSQL analysis completed successfully")
            return self.analysis_results
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise
        finally:
            self.disconnect()
    
    def _assess_compatibility(self, schema_details: List[Dict]) -> Dict[str, Any]:
        """Assess Snowflake compatibility and flag potential issues."""
        flags = {
            'reserved_identifiers': [],
            'wide_tables': [],
            'large_varchars': [],
            'lob_columns': [],
            'complex_constraints': [],
            'triggers': [],
            'functions': []
        }
        
        # Snowflake reserved words (partial list)
        snowflake_reserved = {'ACCOUNT', 'ALL', 'ALTER', 'AND', 'ANY', 'AS', 'BETWEEN', 
                              'BY', 'CASE', 'CAST', 'CHECK', 'COLUMN', 'CONNECT', 'COPY',
                              'CREATE', 'CURRENT', 'DATABASE', 'DELETE', 'DISTINCT', 'DROP',
                              'ELSE', 'EXISTS', 'FALSE', 'FOLLOWING', 'FOR', 'FROM', 'FULL',
                              'GRANT', 'GROUP', 'HAVING', 'ILIKE', 'IN', 'INCREMENT', 'INSERT',
                              'INTERSECT', 'INTO', 'IS', 'ISSUE', 'JOIN', 'LATERAL', 'LEFT',
                              'LIKE', 'LOCALTIME', 'LOCALTIMESTAMP', 'MINUS', 'NATURAL', 'NOT',
                              'NULL', 'OF', 'ON', 'OR', 'ORDER', 'ORGANIZATION', 'QUALIFY',
                              'REGEXP', 'REVOKE', 'RIGHT', 'RLIKE', 'ROW', 'ROWS', 'SAMPLE',
                              'SCHEMA', 'SELECT', 'SET', 'SOME', 'START', 'TABLE', 'TABLESAMPLE',
                              'THEN', 'TO', 'TRIGGER', 'TRUE', 'TRY_CAST', 'UNION', 'UNIQUE',
                              'UPDATE', 'USING', 'VALUES', 'VIEW', 'WHEN', 'WHENEVER', 'WHERE',
                              'WITH'}
        
        for schema in schema_details:
            schema_name = schema['schema_name']
            
            # Check tables
            for table_detail in schema['tables']:
                table_name = table_detail['table_name']
                columns = table_detail['columns']
                
                # Check for reserved identifiers
                if table_name.upper() in snowflake_reserved:
                    flags['reserved_identifiers'].append(f"{schema_name}.{table_name} (table)")
                
                # Check column count (Snowflake limit is ~1000 columns)
                if len(columns) > 500:
                    flags['wide_tables'].append(f"{schema_name}.{table_name} ({len(columns)} columns)")
                
                # Check columns
                for col in columns:
                    col_name = col['column_name']
                    
                    if col_name.upper() in snowflake_reserved:
                        flags['reserved_identifiers'].append(f"{schema_name}.{table_name}.{col_name}")
                    
                    # Check for very large VARCHAR
                    if col['data_type'] in ('character varying', 'text', 'varchar'):
                        if col['character_maximum_length'] and col['character_maximum_length'] > 16000000:
                            flags['large_varchars'].append(f"{schema_name}.{table_name}.{col_name}")
                    
                    # Check for LOB types
                    if col['data_type'] == 'bytea':
                        flags['lob_columns'].append(f"{schema_name}.{table_name}.{col_name} (BYTEA)")
                
                # Check for triggers
                if table_detail['triggers']:
                    for trigger in table_detail['triggers']:
                        flags['triggers'].append(f"{schema_name}.{table_name}.{trigger['trigger_name']}")
            
            # Check for functions/procedures
            if schema['functions']:
                for func in schema['functions']:
                    flags['functions'].append(f"{schema_name}.{func['function_name']} ({func['routine_type']})")
        
        return flags
    
    def save_analysis(self, output_path: str):
        """Save analysis results to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(self.analysis_results, f, indent=2, default=str)
        logger.info(f"Analysis saved to {output_path}")
