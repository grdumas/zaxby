"""
OpenSearch client for querying benchmark results.

Provides connection management and query utilities for retrieving
performance test data from OpenSearch.
"""

import os
import logging
import warnings
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from opensearchpy import OpenSearch, exceptions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _resolve_results_index() -> str:
    """Resolve run/results index: prefer OPENSEARCH_INDEX_RESULTS, else legacy OPENSEARCH_INDEX."""
    return (os.getenv("OPENSEARCH_INDEX_RESULTS") or os.getenv("OPENSEARCH_INDEX") or "").strip()


def _resolve_timeseries_index() -> str:
    """Point-level timeseries index (optional until callers need drill-down)."""
    return (os.getenv("OPENSEARCH_INDEX_TIMESERIES") or "").strip()


class BenchmarkDataSource:
    """Data source connector for OpenSearch benchmark results."""
    
    def __init__(self):
        """Initialize OpenSearch connection using environment variables."""
        load_dotenv()

        self.results_index = _resolve_results_index()
        self.timeseries_index = _resolve_timeseries_index()
        # Backward-compatible alias: same as results index (run documents).
        self.index_name = self.results_index
        
        # Build OpenSearch client configuration
        host = os.getenv('OPENSEARCH_HOST', 'localhost')
        port = int(os.getenv('OPENSEARCH_PORT', '9200'))
        username = os.getenv('OPENSEARCH_USERNAME', 'admin')
        password = os.getenv('OPENSEARCH_PASSWORD', 'admin')
        use_ssl = os.getenv('OPENSEARCH_USE_SSL', 'false').lower() == 'true'
        verify_certs = os.getenv('OPENSEARCH_VERIFY_CERTS', 'false').lower() == 'true'
        
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=(username, password),
            use_ssl=use_ssl,
            verify_certs=verify_certs,
            ssl_show_warn=False,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        
        self._verify_connection()
        
    def _verify_connection(self):
        """Verify connection to OpenSearch and log cluster info."""
        try:
            info = self.client.info()
            logger.info(f"✓ Connected to OpenSearch cluster: {info['cluster_name']}")
            logger.info(f"  Version: {info['version']['number']}")
            
            # Results (run) index
            if self.results_index:
                if self.client.indices.exists(index=self.results_index):
                    count = self.client.count(index=self.results_index)
                    logger.info(f"  Results index '{self.results_index}' contains {count['count']} documents")
                else:
                    logger.warning(f"  Results index '{self.results_index}' does not exist!")
            else:
                logger.warning("  No results index configured (set OPENSEARCH_INDEX or OPENSEARCH_INDEX_RESULTS)")

            if self.timeseries_index:
                if self.client.indices.exists(index=self.timeseries_index):
                    tcount = self.client.count(index=self.timeseries_index)
                    logger.info(f"  Timeseries index '{self.timeseries_index}' contains {tcount['count']} documents")
                else:
                    logger.warning(f"  Timeseries index '{self.timeseries_index}' does not exist!")
                
        except exceptions.ConnectionError as e:
            logger.error(f"✗ Failed to connect to OpenSearch: {e}")
            raise
        except exceptions.AuthenticationException as e:
            logger.error(f"✗ Authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"✗ Unexpected error during connection: {e}")
            raise
    
    def list_indices(self) -> List[str]:
        """
        List all available indices (excluding system indices).
        
        Returns:
            List of index names
        """
        try:
            indices = self.client.indices.get_alias(index="*")
            # Filter out system indices (those starting with '.')
            user_indices = [idx for idx in indices.keys() if not idx.startswith('.')]
            return sorted(user_indices)
        except Exception as e:
            logger.error(f"Error listing indices: {e}")
            return []
    
    def get_sample_documents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve a sample of documents for schema exploration.
        
        Args:
            limit: Number of documents to retrieve
            
        Returns:
            List of document sources
        """
        try:
            response = self.client.search(
                index=self.results_index,
                body={
                    "query": {"match_all": {}},
                    "size": limit
                }
            )
            
            documents = [hit['_source'] for hit in response['hits']['hits']]
            logger.info(f"Retrieved {len(documents)} sample documents")
            return documents
            
        except exceptions.NotFoundError:
            logger.error(f"Index '{self.results_index}' not found")
            return []
        except Exception as e:
            logger.error(f"Error fetching sample documents: {e}")
            return []
    
    def search_results(self, body: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        """
        Run a search against the run/results index only.

        Returns the raw OpenSearch response (including aggregations when requested).
        """
        if not self.results_index:
            raise ValueError(
                "Results index not configured. Set OPENSEARCH_INDEX or OPENSEARCH_INDEX_RESULTS."
            )
        return self.client.search(index=self.results_index, body=body, **kwargs)

    def search_timeseries(self, body: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        """
        Run a search against the timeseries (point-level) index only.

        Do not use for unbounded bulk loads at app startup.
        """
        if not self.timeseries_index:
            raise ValueError(
                "Timeseries index not configured. Set OPENSEARCH_INDEX_TIMESERIES."
            )
        return self.client.search(index=self.timeseries_index, body=body, **kwargs)

    def fetch_timeseries_for_document(
        self,
        document_id: str,
        *,
        size: int = 100,
        document_id_field: str = "metadata.document_id",
    ) -> List[Dict[str, Any]]:
        """
        Fetch a bounded batch of timeseries rows for a parent result document_id.

        Args:
            document_id: Parent run id (metadata.document_id in zathras-results).
            size: Max hits to return (capped for safety).
            document_id_field: Field path in timeseries docs linking to the parent (adjust if mapping uses .keyword).
        """
        if not self.timeseries_index:
            raise ValueError(
                "Timeseries index not configured. Set OPENSEARCH_INDEX_TIMESERIES."
            )
        if size < 1:
            raise ValueError("size must be at least 1")
        size = min(size, 10000)

        body = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {document_id_field: document_id}},
                    ]
                }
            },
            "size": size,
        }
        try:
            response = self.search_timeseries(body)
            hits = response.get("hits", {}).get("hits", [])
            return [hit["_source"] for hit in hits]
        except exceptions.NotFoundError:
            logger.error("Timeseries index %r not found", self.timeseries_index)
            return []
        except Exception as e:
            logger.error("Error fetching timeseries for document_id=%s: %s", document_id, e)
            return []

    def scroll_results(self, max_docs: int = 10000) -> List[Dict[str, Any]]:
        """
        Scroll the run/results index up to max_docs documents.

        Never targets the timeseries index. Prefer this over deprecated get_all_documents().
        """
        if not self.results_index:
            logger.error("No results index configured (OPENSEARCH_INDEX or OPENSEARCH_INDEX_RESULTS)")
            return []
        try:
            all_documents: List[Dict[str, Any]] = []
            batch_size = 1000

            response = self.client.search(
                index=self.results_index,
                scroll="2m",
                size=batch_size,
                body={"query": {"match_all": {}}},
            )

            scroll_id = response["_scroll_id"]
            hits = response["hits"]["hits"]
            all_documents.extend([hit["_source"] for hit in hits])

            while len(hits) > 0 and len(all_documents) < max_docs:
                response = self.client.scroll(scroll_id=scroll_id, scroll="2m")
                scroll_id = response["_scroll_id"]
                hits = response["hits"]["hits"]
                all_documents.extend([hit["_source"] for hit in hits])

            try:
                self.client.clear_scroll(scroll_id=scroll_id)
            except Exception:
                pass

            logger.info(f"Retrieved {len(all_documents)} total documents from results index")
            return all_documents[:max_docs]

        except exceptions.NotFoundError:
            logger.error(f"Index '{self.results_index}' not found")
            return []
        except Exception as e:
            logger.error(f"Error scrolling results index: {e}")
            return []

    def get_all_documents(self, max_docs: int = 10000) -> List[Dict[str, Any]]:
        """
        Retrieve documents from the run/results index using scroll.

        Deprecated: use scroll_results(max_docs=...) instead.
        """
        warnings.warn(
            "get_all_documents is deprecated; use scroll_results(max_docs=...) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.scroll_results(max_docs=max_docs)
    
    def query_with_filters(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Fetch benchmark results with optional filtering.
        
        Args:
            filters: Dictionary of filters to apply (structure depends on schema)
            limit: Maximum number of results to return
            
        Returns:
            List of benchmark result documents
        """
        # Build query
        if not filters:
            query = {"query": {"match_all": {}}}
        else:
            # Build bool query with filters
            must_clauses = []
            
            # Add filter clauses based on provided filters
            # This will be refined once we understand the schema
            for field, value in filters.items():
                if isinstance(value, list):
                    # Multiple values - use terms query
                    must_clauses.append({"terms": {field: value}})
                else:
                    # Single value - use term query
                    must_clauses.append({"term": {field: value}})
            
            query = {
                "query": {
                    "bool": {
                        "must": must_clauses
                    }
                }
            }
        
        try:
            response = self.client.search(
                index=self.results_index,
                body=query,
                size=limit
            )
            
            documents = [hit['_source'] for hit in response['hits']['hits']]
            logger.info(f"Query returned {len(documents)} documents")
            return documents
            
        except exceptions.RequestError as e:
            logger.error(f"Invalid query: {e}")
            return []
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []
    
    def get_field_aggregations(self, field: str, size: int = 100) -> Dict[str, int]:
        """
        Get aggregations (unique values and counts) for a specific field.
        Useful for discovering filter options.
        
        Args:
            field: Field name to aggregate (must be keyword type)
            size: Maximum number of buckets to return
            
        Returns:
            Dictionary mapping field values to document counts
        """
        try:
            response = self.client.search(
                index=self.results_index,
                body={
                    "size": 0,  # We only want aggregations, not documents
                    "aggs": {
                        "field_values": {
                            "terms": {
                                "field": field,
                                "size": size
                            }
                        }
                    }
                }
            )
            
            buckets = response['aggregations']['field_values']['buckets']
            result = {bucket['key']: bucket['doc_count'] for bucket in buckets}
            logger.info(f"Found {len(result)} unique values for field '{field}'")
            return result
            
        except Exception as e:
            logger.error(f"Error getting aggregations for field '{field}': {e}")
            return {}
    
    def explore_schema(self) -> Dict[str, Any]:
        """
        Explore and analyze the schema by examining sample documents.
        
        Returns:
            Dictionary with schema information
        """
        samples = self.get_sample_documents(limit=50)
        
        if not samples:
            return {"error": "No documents found"}
        
        # Collect all fields across samples
        all_fields = set()
        field_types = {}
        field_examples = {}
        
        for doc in samples:
            self._extract_fields(doc, all_fields, field_types, field_examples)
        
        schema_info = {
            "total_documents": len(samples),
            "fields": sorted(list(all_fields)),
            "field_count": len(all_fields),
            "field_types": field_types,
            "field_examples": field_examples
        }
        
        logger.info(f"Schema exploration found {len(all_fields)} unique fields")
        return schema_info
    
    def _extract_fields(
        self,
        doc: Dict[str, Any],
        all_fields: set,
        field_types: Dict[str, set],
        field_examples: Dict[str, Any],
        prefix: str = ""
    ):
        """
        Recursively extract field names and types from nested documents.
        
        Args:
            doc: Document or subdocument to analyze
            all_fields: Set to accumulate field names
            field_types: Dictionary mapping field names to observed types
            field_examples: Dictionary mapping field names to example values
            prefix: Field path prefix for nested fields
        """
        for key, value in doc.items():
            field_name = f"{prefix}{key}" if prefix else key
            all_fields.add(field_name)
            
            # Track type
            value_type = type(value).__name__
            if field_name not in field_types:
                field_types[field_name] = set()
            field_types[field_name].add(value_type)
            
            # Store example (first occurrence)
            if field_name not in field_examples:
                field_examples[field_name] = value
            
            # Recurse for nested objects (but not lists)
            if isinstance(value, dict):
                self._extract_fields(
                    value, all_fields, field_types, field_examples,
                    prefix=f"{field_name}."
                )


def main():
    """Test the OpenSearch connection and explore schema."""
    try:
        client = BenchmarkDataSource()
        
        print("\n" + "="*60)
        print("AVAILABLE INDICES")
        print("="*60)
        indices = client.list_indices()
        for idx in indices:
            print(f"  - {idx}")
        
        print("\n" + "="*60)
        print("SCHEMA EXPLORATION")
        print("="*60)
        schema = client.explore_schema()
        
        if "error" in schema:
            print(f"Error: {schema['error']}")
        else:
            print(f"\nTotal documents sampled: {schema['total_documents']}")
            print(f"Total unique fields: {schema['field_count']}")
            print("\nFields and types:")
            for field in schema['fields']:
                types = ', '.join(schema['field_types'][field])
                example = schema['field_examples'][field]
                # Truncate long examples
                if isinstance(example, str) and len(example) > 50:
                    example = example[:47] + "..."
                print(f"  {field:40s} ({types:15s}) = {example}")
        
        print("\n" + "="*60)
        print("SAMPLE DOCUMENTS")
        print("="*60)
        import json
        samples = client.get_sample_documents(limit=3)
        for i, doc in enumerate(samples, 1):
            print(f"\nDocument {i}:")
            print(json.dumps(doc, indent=2)[:500])  # Truncate for readability
            if len(json.dumps(doc, indent=2)) > 500:
                print("... (truncated)")
        
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        print("\nPlease ensure:")
        print("1. You have created a .env file (copy from .env.example)")
        print("2. OpenSearch connection details are correct")
        print("3. OpenSearch server is running and accessible")


if __name__ == "__main__":
    main()



