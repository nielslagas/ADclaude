from supabase import create_client, Client
from app.core.config import settings
import uuid
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Any, Optional
from app.db.postgres import get_db, engine

# Mock implementation for local development
class MockSupabaseClient:
    """
    Mock Supabase client that uses direct PostgreSQL operations
    instead of Supabase REST API for local development
    """
    def __init__(self):
        self.current_table = None
        self.query_params = {}
        self.storage = MockStorage()
    
    def table(self, table_name: str):
        """Set the current table and return self for method chaining"""
        self.current_table = table_name
        self.query_params = {}
        return self
    
    def select(self, columns: str = "*"):
        """Mock select method"""
        self.query_params['select'] = columns
        return self
    
    def eq(self, column: str, value: Any):
        """Add an equality condition"""
        if 'where' not in self.query_params:
            self.query_params['where'] = []
        self.query_params['where'].append((column, '=', value))
        return self
    
    def neq(self, column: str, value: Any):
        """Add a not equal condition"""
        if 'where' not in self.query_params:
            self.query_params['where'] = []
        self.query_params['where'].append((column, '!=', value))
        return self
    
    def order(self, column: str, desc: bool = False):
        """Add an order by clause"""
        self.query_params['order_by'] = column
        self.query_params['desc'] = desc
        return self
    
    def execute(self):
        """Execute the built query"""
        try:
            if self.current_table == "Case":
                return self._execute_case_query()
            elif self.current_table == "Document":
                return self._execute_document_query()
            elif self.current_table == "DocumentChunk":
                return self._execute_document_chunk_query()
            elif self.current_table == "Report":
                return self._execute_report_query()
            else:
                # Default empty response
                return MockResponse([])
        except Exception as e:
            print(f"Error executing mock query: {str(e)}")
            return MockResponse([])
    
    def insert(self, data: Dict[str, Any]):
        """Insert data into the table"""
        try:
            if self.current_table == "Case":
                return self._insert_case(data)
            elif self.current_table == "Document":
                return self._insert_document(data)
            elif self.current_table == "DocumentChunk":
                return self._insert_document_chunk(data)
            elif self.current_table == "Report":
                return self._insert_report(data)
            else:
                # Default mock response
                return MockResponse([{"id": str(uuid.uuid4())}])
        except Exception as e:
            print(f"Error with insert: {str(e)}")
            return MockResponse([])
    
    def update(self, data: Dict[str, Any]):
        """Update data in the table"""
        self.update_data = data
        return self
    
    def delete(self):
        """Delete from the table"""
        self.delete_flag = True
        return self
    
    def _build_where_clause(self):
        """Build a SQL WHERE clause from query params"""
        if 'where' not in self.query_params or not self.query_params['where']:
            return "", {}
        
        conditions = []
        params = {}
        
        for i, (column, op, value) in enumerate(self.query_params['where']):
            param_name = f"param_{i}"
            conditions.append(f"{column} {op} :{param_name}")
            params[param_name] = value
        
        return "WHERE " + " AND ".join(conditions), params
    
    def _execute_case_query(self):
        """Execute a query for the Case table"""
        # Build the SQL query
        select_clause = self.query_params.get('select', '*')
        where_clause, params = self._build_where_clause()
        order_clause = ""
        
        if 'order_by' in self.query_params:
            direction = "DESC" if self.query_params.get('desc', False) else "ASC"
            order_clause = f"ORDER BY {self.query_params['order_by']} {direction}"
        
        sql = f"SELECT {select_clause} FROM case_table {where_clause} {order_clause}"
        
        # Execute the query
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql), params)
                rows = result.fetchall()
                
                # Convert to list of dicts
                data = []
                for row in rows:
                    # Convert SQL row to dict
                    row_dict = {col: getattr(row, col) for col in row._fields}
                    data.append(row_dict)
                
                return MockResponse(data)
        except SQLAlchemyError as e:
            print(f"Database error: {str(e)}")
            return MockResponse([])
    
    def _insert_case(self, data):
        """Insert into the Case table"""
        # Generate an ID if not provided
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        
        # Add timestamps
        now = datetime.utcnow().isoformat()
        data['created_at'] = now
        data['updated_at'] = now
        
        # Build param dict
        params = {k: v for k, v in data.items()}
        
        # Build the field and value parts of the INSERT
        fields = ", ".join(params.keys())
        placeholders = ", ".join([f":{k}" for k in params.keys()])
        
        sql = f"INSERT INTO case_table ({fields}) VALUES ({placeholders}) RETURNING *"
        
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql), params)
                conn.commit()
                row = result.fetchone()
                
                if row:
                    # Convert SQL row to dict
                    row_dict = {col: getattr(row, col) for col in row._fields}
                    return MockResponse([row_dict])
                return MockResponse([])
        except SQLAlchemyError as e:
            print(f"Database error on insert: {str(e)}")
            return MockResponse([])
    
    # ... similar methods for other tables
    
    def _execute_document_query(self):
        """Placeholder for document queries"""
        return MockResponse([])
    
    def _insert_document(self, data):
        """Placeholder for document inserts"""
        data['id'] = str(uuid.uuid4())
        return MockResponse([data])
    
    def _execute_document_chunk_query(self):
        """Placeholder for document chunk queries"""
        return MockResponse([])
    
    def _insert_document_chunk(self, data):
        """Placeholder for document chunk inserts"""
        data['id'] = str(uuid.uuid4())
        return MockResponse([data])
    
    def _execute_report_query(self):
        """Placeholder for report queries"""
        return MockResponse([])
    
    def _insert_report(self, data):
        """Placeholder for report inserts"""
        data['id'] = str(uuid.uuid4())
        return MockResponse([data])

    def rpc(self, function_name, params=None):
        """Mock for RPC calls"""
        return self

# Mock class for Supabase storage
class MockStorage:
    def __init__(self):
        self.buckets = {}

    def from_(self, bucket: str):
        """Select a bucket"""
        if bucket not in self.buckets:
            self.buckets[bucket] = {}
        return MockBucket(self.buckets[bucket])

class MockBucket:
    def __init__(self, files):
        self.files = files
    
    def upload(self, path: str, file, file_options=None):
        """Mock file upload - just store in memory"""
        self.files[path] = file
        return path
    
    def download(self, path: str):
        """Mock file download"""
        return self.files.get(path, b'')
    
    def remove(self, paths: List[str]):
        """Mock file removal"""
        for path in paths:
            if path in self.files:
                del self.files[path]
        return True

class MockResponse:
    def __init__(self, data, error=None):
        self.data = data
        self.error = error

def get_supabase_client():
    """
    Get a Supabase client - either the real one or a mock for local development
    """
    try:
        # Try to create a real Supabase client if credentials are available
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        else:
            # Use mock client for local development
            print("Using mock Supabase client for local development")
            return MockSupabaseClient()
    except Exception as e:
        print(f"Error creating Supabase client: {str(e)}")
        print("Falling back to mock Supabase client")
        return MockSupabaseClient()

supabase = get_supabase_client()
