import uuid
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, TypeVar, Generic, BinaryIO
from sqlalchemy import text, Table, Column, String, MetaData
from sqlalchemy.exc import SQLAlchemyError
from app.db.postgres import engine
from app.core.config import settings

T = TypeVar('T')

# Custom JSON encoder that can handle UUIDs
class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            # Convert UUID to string
            return str(obj)
        return json.JSONEncoder.default(self, obj)

class DatabaseService:
    """
    Service for direct database operations via SQLAlchemy.
    Replaces Supabase client functionality for local development.
    """
    
    def __init__(self):
        self.engine = engine
        # Cache for table structures
        self._tables = {}
        
    def get_rows(self, table_name: str, where_conditions: Optional[Dict[str, Any]] = None, 
                 order_by: Optional[str] = None, desc: bool = False) -> List[Dict[str, Any]]:
        """
        Get rows from a table with optional filtering and ordering
        """
        try:
            # Build WHERE clause
            where_clause = ""
            params = {}
            
            if where_conditions:
                conditions = []
                for i, (column, value) in enumerate(where_conditions.items()):
                    if isinstance(value, tuple) and len(value) == 2:
                        # Operator and value provided as (operator, value)
                        operator, actual_value = value
                        conditions.append(f"{column} {operator} :param_{i}")
                        params[f"param_{i}"] = actual_value
                    else:
                        # Default to equality
                        conditions.append(f"{column} = :param_{i}")
                        params[f"param_{i}"] = value
                
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)
            
            # Build ORDER BY clause
            order_clause = ""
            if order_by:
                direction = "DESC" if desc else "ASC"
                order_clause = f"ORDER BY {order_by} {direction}"
            
            # IMPORTANT: For PostgreSQL reserved words like 'case', we need to use double quotes
            if table_name == "case":
                table_name = "case_table"
                
            print(f"Getting rows from table: {table_name}")
            
            # Build and execute query
            query = f"SELECT * FROM {table_name} {where_clause} {order_clause}"
            
            with self.engine.connect() as connection:
                result = connection.execute(text(query), params)
                rows = result.fetchall()
                
                # Convert rows to dictionaries
                rows_dict = [self._row_to_dict(row) for row in rows]
                
                # For reports, we need to parse the JSON fields
                if table_name == "report":
                    for row in rows_dict:
                        # Parse content and metadata if they are JSON strings
                        if "content" in row and isinstance(row["content"], str):
                            try:
                                row["content"] = json.loads(row["content"])
                            except json.JSONDecodeError:
                                print(f"Failed to decode content JSON: {row['content']}")
                        
                        if "metadata" in row and isinstance(row["metadata"], str):
                            try:
                                row["metadata"] = json.loads(row["metadata"])
                                # For compatibility with the Report model
                                row["report_metadata"] = row["metadata"]
                            except json.JSONDecodeError:
                                print(f"Failed to decode metadata JSON: {row['metadata']}")
                
                return rows_dict
                
        except SQLAlchemyError as e:
            print(f"Database error in get_rows: {str(e)}")
            return []
    
    def get_row_by_id(self, table_name: str, id_value: Any) -> Optional[Dict[str, Any]]:
        """
        Get a single row by ID
        """
        rows = self.get_rows(table_name, {"id": id_value})
        
        # If this is a report, we need to parse the JSON fields
        if table_name == "report" and rows:
            row = rows[0]
            # Parse content and metadata if they are JSON strings
            if "content" in row and isinstance(row["content"], str):
                try:
                    row["content"] = json.loads(row["content"])
                except json.JSONDecodeError:
                    print(f"Failed to decode content JSON: {row['content']}")
            
            if "metadata" in row and isinstance(row["metadata"], str):
                try:
                    row["metadata"] = json.loads(row["metadata"])
                    # For compatibility with the Report model
                    row["report_metadata"] = row["metadata"]
                except json.JSONDecodeError:
                    print(f"Failed to decode metadata JSON: {row['metadata']}")
        
        return rows[0] if rows else None
    
    def create_row(self, table_name: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new row in the specified table
        """
        try:
            # Set ID if not provided
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            
            # Table-specific adjustments
            if table_name == "document_chunk":
                # Document chunk table doesn't have updated_at field
                # Set timestamps: only created_at for document_chunk
                if 'created_at' not in data:
                    data['created_at'] = datetime.utcnow().isoformat()
            else:
                # Set timestamps for all other tables
                now = datetime.utcnow().isoformat()
                if 'created_at' not in data:
                    data['created_at'] = now
                if 'updated_at' not in data:
                    data['updated_at'] = now
            
            # Build query parts
            columns = list(data.keys())
            placeholders = [f":{col}" for col in columns]
            
            # IMPORTANT: For PostgreSQL reserved words like 'case', we need to use double quotes
            if table_name == "case":
                table_name = "case_table"
                
            print(f"Creating row in table: {table_name}")
            
            query = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """
            
            with self.engine.connect() as connection:
                result = connection.execute(text(query), data)
                connection.commit()
                
                row = result.fetchone()
                return self._row_to_dict(row) if row else None
                
        except SQLAlchemyError as e:
            print(f"Database error in create_row: {str(e)}")
            return None
    
    def update_row(self, table_name: str, id_value: Any, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a row by ID
        """
        try:
            # Add updated_at timestamp
            if 'updated_at' not in data:
                data['updated_at'] = datetime.utcnow().isoformat()
            
            # Build SET clause
            set_items = [f"{key} = :{key}" for key in data.keys()]
            set_clause = ", ".join(set_items)
            
            # Include ID in parameters
            params = {**data, "id": id_value}
            
            # IMPORTANT: For PostgreSQL reserved words like 'case', we need to use double quotes
            if table_name == "case":
                table_name = "case_table"
                
            print(f"Updating row in table: {table_name}")
            
            query = f"""
                UPDATE {table_name}
                SET {set_clause}
                WHERE id = :id
                RETURNING *
            """
            
            with self.engine.connect() as connection:
                result = connection.execute(text(query), params)
                connection.commit()
                
                row = result.fetchone()
                return self._row_to_dict(row) if row else None
                
        except SQLAlchemyError as e:
            print(f"Database error in update_row: {str(e)}")
            return None
    
    def delete_row(self, table_name: str, id_value: Any) -> bool:
        """
        Delete a row by ID
        """
        try:
            # IMPORTANT: For PostgreSQL reserved words like 'case', we need to use double quotes
            if table_name == "case":
                table_name = "case_table"
                
            print(f"Deleting row from table: {table_name}")
            
            query = f"DELETE FROM {table_name} WHERE id = :id"
            
            with self.engine.connect() as connection:
                result = connection.execute(text(query), {"id": id_value})
                connection.commit()
                
                return result.rowcount > 0
                
        except SQLAlchemyError as e:
            print(f"Database error in delete_row: {str(e)}")
            return False
    
    def _row_to_dict(self, row) -> Dict[str, Any]:
        """
        Convert a SQLAlchemy Row to a dictionary
        """
        if not row:
            return {}
            
        return {key: value for key, value in row._mapping.items()}
        
    # File storage operations
    def get_document_storage_path(self, user_id: str, case_id: str, filename: str) -> str:
        """
        Create a storage path for a document
        """
        # Create directories if they don't exist
        storage_dir = os.path.join(settings.STORAGE_PATH, "documents", user_id, case_id)
        os.makedirs(storage_dir, exist_ok=True)
        
        return os.path.join(storage_dir, filename)
    
    def save_document_file(self, file_content: bytes, storage_path: str) -> bool:
        """
        Save a document file to the storage path
        """
        try:
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            
            # Write the file
            with open(storage_path, "wb") as f:
                f.write(file_content)
                
            return True
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            return False
    
    def delete_document_file(self, storage_path: str) -> bool:
        """
        Delete a document file from storage
        """
        try:
            if os.path.exists(storage_path):
                os.remove(storage_path)
            return True
        except Exception as e:
            print(f"Error deleting file: {str(e)}")
            return False
            
    def get_document_file(self, storage_path: str) -> Optional[bytes]:
        """
        Get a document file from storage
        """
        try:
            if os.path.exists(storage_path):
                with open(storage_path, "rb") as f:
                    return f.read()
            return None
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return None

    # Case-specific methods
    def get_cases_for_user(self, user_id: str, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """
        Get all cases for a specific user
        """
        where_conditions = {"user_id": user_id}
        if not include_deleted:
            where_conditions["status"] = ("!=", "deleted")
        
        return self.get_rows("case_table", where_conditions, "created_at", True)
    
    def get_case(self, case_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific case by ID and user ID
        """
        try:
            rows = self.get_rows("case_table", {"id": case_id, "user_id": user_id})
            return rows[0] if rows else None
        except Exception as e:
            print(f"Error in get_case({case_id}, {user_id}): {str(e)}")
            return None
    
    def create_case(self, user_id: str, title: str, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a new case for a user
        """
        data = {
            "title": title,
            "user_id": user_id,
            "status": "active"
        }
        
        if description:
            data["description"] = description
        
        print(f"Creating case with table name: case_table")    
        return self.create_row("case_table", data)
    
    def update_case(self, case_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a case
        """
        return self.update_row("case_table", case_id, data)
    
    def delete_case(self, case_id: str, user_id: str, hard_delete: bool = False) -> bool:
        """
        Delete a case (soft delete by default)
        """
        if hard_delete:
            return self.delete_row("case_table", case_id)
        else:
            # Soft delete by updating status
            case = self.update_row("case_table", case_id, {"status": "deleted"})
            return case is not None
    
    # Document-specific methods
    def get_documents_for_case(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Get all documents for a specific case
        """
        return self.get_rows("document", {"case_id": case_id}, "created_at", True)
    
    def get_document(self, document_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific document by ID and user ID
        """
        rows = self.get_rows("document", {"id": document_id, "user_id": user_id})
        return rows[0] if rows else None
    
    def create_document(self, case_id: str, user_id: str, filename: str, 
                       storage_path: str, mimetype: str, size: int) -> Optional[Dict[str, Any]]:
        """
        Create a new document record
        """
        data = {
            "case_id": case_id,
            "user_id": user_id,
            "filename": filename,
            "storage_path": storage_path,
            "mimetype": mimetype,
            "size": size,
            "status": "processing"
        }
            
        return self.create_row("document", data)
    
    def update_document_status(self, document_id: str, status: str, error: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Update a document's status
        """
        data = {"status": status}
        if error:
            data["error"] = error
            
        return self.update_row("document", document_id, data)
        
    # Document chunk methods
    def create_document_chunk(self, document_id: str, content: str, chunk_index: int,
                             metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Create a new document chunk
        """
        data = {
            "document_id": document_id,
            "content": content,
            "chunk_index": chunk_index
        }
        
        if metadata:
            # Convert metadata to JSON string using UUIDEncoder
            from app.utils.vector_store import UUIDEncoder
            data["metadata"] = json.dumps(metadata, cls=UUIDEncoder)
            
        return self.create_row("document_chunk", data)
        
    def update_document_chunk_embedding(self, chunk_id: str, embedding: List[float]) -> Optional[Dict[str, Any]]:
        """
        Update a document chunk with its embedding vector
        """
        try:
            # Embeddings need special handling for the vector type
            query = """
                UPDATE document_chunk
                SET embedding = :embedding
                WHERE id = :id
                RETURNING *
            """
            
            params = {
                "id": chunk_id,
                "embedding": embedding  # SQLAlchemy will convert the list to a vector
            }
            
            with self.engine.connect() as connection:
                result = connection.execute(text(query), params)
                connection.commit()
                
                row = result.fetchone()
                return self._row_to_dict(row) if row else None
                
        except SQLAlchemyError as e:
            print(f"Database error in update_document_chunk_embedding: {str(e)}")
            return None
            
    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a document
        """
        return self.get_rows("document_chunk", {"document_id": document_id}, "chunk_index")
    
    def get_document_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific document chunk by ID
        """
        rows = self.get_rows("document_chunk", {"id": chunk_id})
        
        if not rows:
            return None
            
        chunk = rows[0]
        
        # Parse metadata if it's a JSON string
        if "metadata" in chunk and isinstance(chunk["metadata"], str):
            try:
                chunk["metadata"] = json.loads(chunk["metadata"])
            except json.JSONDecodeError:
                print(f"Failed to decode chunk metadata JSON: {chunk['metadata']}")
                
        return chunk
    def similarity_search(self, query_embedding: List[float], case_id: str,
                         match_threshold: float = 0.5, match_count: int = 10) -> List[Dict[str, Any]]:
        """
        Perform a similarity search on document chunks using vector search
        with enhanced error handling and fallback
        """
        try:
            # Check if the stored procedure exists
            check_function_query = """
                SELECT COUNT(*) FROM pg_proc 
                WHERE proname = 'search_document_chunks_vector' 
                AND pg_function_is_visible(oid);
            """
            
            with self.engine.connect() as connection:
                check_result = connection.execute(text(check_function_query))
                function_exists = check_result.scalar() > 0
            
            if function_exists:
                # Primary approach: Use the optimized stored procedure
                query = """
                    SELECT * FROM search_document_chunks_vector(
                        :query_embedding,
                        :case_id,
                        :match_threshold,
                        :match_count
                    )
                """
                
                params = {
                    "query_embedding": query_embedding,
                    "case_id": case_id,
                    "match_threshold": match_threshold,
                    "match_count": match_count
                }
                
                with self.engine.connect() as connection:
                    result = connection.execute(text(query), params)
                    rows = result.fetchall()
                    
                    # Convert rows to dictionaries
                    return [self._row_to_dict(row) for row in rows]
            else:
                # Fallback: Manual similarity search if stored procedure doesn't exist
                print("WARNING: search_document_chunks_vector procedure not found, using fallback method")
                
                # First get document IDs for this case
                case_docs_query = """
                    SELECT id FROM document WHERE case_id = :case_id AND status = 'processed'
                """
                
                with self.engine.connect() as connection:
                    docs_result = connection.execute(text(case_docs_query), {"case_id": case_id})
                    document_ids = [row[0] for row in docs_result.fetchall()]
                
                if not document_ids:
                    print(f"No processed documents found for case {case_id}")
                    return []
                
                # Format document IDs for IN clause
                doc_ids_str = ", ".join(f"'{doc_id}'" for doc_id in document_ids)
                
                # Perform similarity search with cosine distance
                fallback_query = f"""
                    SELECT 
                        chunk_id as id,
                        document_id,
                        content,
                        metadata,
                        1 - (embedding <=> :query_embedding) as similarity
                    FROM 
                        document_embeddings
                    WHERE 
                        document_id IN ({doc_ids_str})
                        AND 1 - (embedding <=> :query_embedding) >= :match_threshold
                    ORDER BY 
                        embedding <=> :query_embedding
                    LIMIT 
                        :match_count
                """
                
                with self.engine.connect() as connection:
                    result = connection.execute(
                        text(fallback_query), 
                        {
                            "query_embedding": query_embedding,
                            "match_threshold": match_threshold,
                            "match_count": match_count
                        }
                    )
                    rows = result.fetchall()
                    
                    # Convert rows to dictionaries
                    return [self._row_to_dict(row) for row in rows]
                
        except SQLAlchemyError as e:
            print(f"Database error in similarity_search: {str(e)}")
            return []
    
    # Report-specific methods
    def get_reports_for_case(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Get all reports for a specific case
        """
        return self.get_rows("report", {"case_id": case_id}, "created_at", True)
    
    def get_report(self, report_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific report by ID and user ID
        """
        rows = self.get_rows("report", {"id": report_id, "user_id": user_id})
        return rows[0] if rows else None
    
    def create_report(self, case_id: str, user_id: str, title: str, 
                     template_id: str) -> Optional[Dict[str, Any]]:
        """
        Create a new report
        """
        data = {
            "case_id": case_id,
            "user_id": user_id,
            "title": title,
            "template_id": template_id,
            "status": "processing",
            "content": "{}"  # Empty JSON content
        }
        
        # Make sure content and metadata are JSON strings
        if "content" in data and isinstance(data["content"], dict):
            # Use the custom encoder
            data["content"] = json.dumps(data["content"], cls=UUIDEncoder)
            
        if "metadata" in data and isinstance(data["metadata"], dict):
            # Use the custom encoder
            data["metadata"] = json.dumps(data["metadata"], cls=UUIDEncoder)
        elif "report_metadata" in data and isinstance(data["report_metadata"], dict):
            # Handle report_metadata -> metadata conversion
            data["metadata"] = json.dumps(data["report_metadata"], cls=UUIDEncoder)
            
        return self.create_row("report", data)
    
    def update_report(self, report_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a report with built-in safety filter for 'dangerous_content' 
        """
        # Filter out dangerous_content mentions before processing
        if "content" in data and isinstance(data["content"], dict):
            for section_id, content in data["content"].items():
                if isinstance(content, str) and "dangerous_content" in content:
                    print(f"WARNING: Filtering dangerous_content from section {section_id}")
                    data["content"][section_id] = "Op basis van de beschikbare documenten is een objectieve analyse gemaakt. Voor meer specifieke informatie zijn aanvullende documenten gewenst."
        
        # Convert dict values to JSON strings for PostgreSQL
        processed_data = {}
        for key, value in data.items():
            # Handle special field conversions
            if key == "content" and isinstance(value, dict):
                # Use the custom encoder
                processed_data["content"] = json.dumps(value, cls=UUIDEncoder)
            elif key == "metadata" and isinstance(value, dict):
                # Convert metadata to JSON
                # Filter out any error messages containing dangerous_content
                if "sections" in value:
                    for section_id, section_data in value["sections"].items():
                        if "error" in section_data and isinstance(section_data["error"], str) and "dangerous_content" in section_data["error"]:
                            section_data["error"] = "Content generation failed"
                processed_data["metadata"] = json.dumps(value, cls=UUIDEncoder)
            elif key == "report_metadata" and isinstance(value, dict):
                # Handle report_metadata -> metadata conversion
                # Filter out any error messages containing dangerous_content
                if "sections" in value:
                    for section_id, section_data in value["sections"].items():
                        if "error" in section_data and isinstance(section_data["error"], str) and "dangerous_content" in section_data["error"]:
                            section_data["error"] = "Content generation failed"
                processed_data["metadata"] = json.dumps(value, cls=UUIDEncoder)
            elif key == "error" and isinstance(value, str) and "dangerous_content" in value:
                # Filter out error messages containing dangerous_content
                processed_data[key] = "Rapportgeneratie kon niet worden voltooid"
            else:
                processed_data[key] = value
                
        print(f"Processed report data for update: {processed_data}")
        return self.update_row("report", report_id, processed_data)

# Create a singleton instance
db_service = DatabaseService()