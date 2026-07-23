"""
Tests for OpenSearch client module.
"""

import logging
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.opensearch_client import BenchmarkDataSource


@pytest.fixture
def mock_opensearch_client():
    """Create a mock OpenSearch client."""
    with patch('src.opensearch_client.OpenSearch') as mock_client:
        # Mock the info() response
        mock_client.return_value.info.return_value = {
            'cluster_name': 'test-cluster',
            'version': {'number': '3.2.0'}
        }
        
        # Mock indices.exists()
        mock_client.return_value.indices.exists.return_value = True
        
        # Mock count()
        mock_client.return_value.count.return_value = {'count': 100}
        
        yield mock_client


def test_client_initialization(mock_opensearch_client):
    """Test BenchmarkDataSource initialization."""
    with patch.dict('os.environ', {
        'OPENSEARCH_HOST': 'localhost',
        'OPENSEARCH_PORT': '9200',
        'OPENSEARCH_INDEX': 'test-index'
    }):
        client = BenchmarkDataSource()
        
        assert client.index_name == 'test-index'
        assert client.results_index == 'test-index'
        assert client.timeseries_index == ''
        assert client.client is not None


def test_results_index_prefers_opensearch_index_results(mock_opensearch_client):
    """OPENSEARCH_INDEX_RESULTS wins when both legacy and new vars are set."""
    with patch.dict('os.environ', {
        'OPENSEARCH_HOST': 'localhost',
        'OPENSEARCH_PORT': '9200',
        'OPENSEARCH_INDEX': 'legacy-index',
        'OPENSEARCH_INDEX_RESULTS': 'canonical-results',
    }):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            assert client.results_index == 'canonical-results'
            assert client.index_name == 'canonical-results'


def test_search_results_uses_results_index(mock_opensearch_client):
    """search_results passes the results index name to the OpenSearch client."""
    with patch.dict('os.environ', {'OPENSEARCH_INDEX': 'test-index'}):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            client.client.search = Mock(return_value={'hits': {'hits': []}})
            client.search_results({"query": {"match_all": {}}, "size": 2})
            client.client.search.assert_called_once()
            _, kwargs = client.client.search.call_args
            assert kwargs['index'] == 'test-index'


def test_search_timeseries_requires_configured_index(mock_opensearch_client):
    """search_timeseries raises when OPENSEARCH_INDEX_TIMESERIES is unset."""
    with patch.dict('os.environ', {'OPENSEARCH_INDEX': 'test-index'}):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            with pytest.raises(ValueError, match="Timeseries index not configured"):
                client.search_timeseries({"query": {"match_all": {}}})


def test_fetch_timeseries_for_document(mock_opensearch_client):
    """Bounded timeseries query targets the timeseries index and returns sources."""
    with patch.dict('os.environ', {
        'OPENSEARCH_INDEX': 'ri',
        'OPENSEARCH_INDEX_TIMESERIES': 'tsi',
    }):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            client.client.search = Mock(
                return_value={'hits': {'hits': [{'_source': {'k': 1}}]}}
            )
            rows = client.fetch_timeseries_for_document('parent-doc-id', size=5)
            assert rows == [{'k': 1}]
            _, kwargs = client.client.search.call_args
            assert kwargs['index'] == 'tsi'
            assert kwargs['body']['size'] == 5
            assert kwargs['body']['query']['bool']['must'][0]['term'][
                'metadata.document_id'
            ] == 'parent-doc-id'
            # Verify sort clause for ordered results
            assert kwargs['body']['sort'] == [{"metadata.sequence": {"order": "asc"}}]


def test_get_all_documents_deprecation(mock_opensearch_client):
    """get_all_documents is deprecated in favor of scroll_results."""
    with patch.dict('os.environ', {'OPENSEARCH_INDEX': 'test-index'}):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            client.scroll_results = Mock(return_value=[])
            with pytest.warns(DeprecationWarning, match="scroll_results"):
                client.get_all_documents(max_docs=42)
            client.scroll_results.assert_called_once_with(max_docs=42)


def test_legacy_methods_use_results_index(mock_opensearch_client):
    """get_sample_documents, query_with_filters, get_field_aggregations target results_index."""
    mock_search_response = {
        "hits": {"hits": [{"_source": {"x": 1}}]},
        "aggregations": {"field_values": {"buckets": [{"key": "k", "doc_count": 1}]}},
    }
    with patch.dict(
        "os.environ",
        {
            "OPENSEARCH_HOST": "localhost",
            "OPENSEARCH_PORT": "9200",
            "OPENSEARCH_INDEX_RESULTS": "canonical-idx",
        },
    ):
        with patch.object(BenchmarkDataSource, "_verify_connection"):
            client = BenchmarkDataSource()
            client.client.search = Mock(return_value=mock_search_response)

            client.get_sample_documents(limit=5)
            assert client.client.search.call_args[1]["index"] == "canonical-idx"

            client.client.search.reset_mock()
            client.query_with_filters(filters={"os_version": "9.5"}, limit=10)
            assert client.client.search.call_args[1]["index"] == "canonical-idx"

            client.client.search.reset_mock()
            client.get_field_aggregations("metadata.cloud_provider.keyword", size=5)
            assert client.client.search.call_args[1]["index"] == "canonical-idx"


def test_get_sample_documents(mock_opensearch_client):
    """Test retrieving sample documents."""
    # Mock search response
    mock_response = {
        'hits': {
            'hits': [
                {'_source': {'test': 'doc1'}},
                {'_source': {'test': 'doc2'}}
            ]
        }
    }
    
    with patch.dict('os.environ', {'OPENSEARCH_INDEX': 'test-index'}):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            client.client.search = Mock(return_value=mock_response)
            
            docs = client.get_sample_documents(limit=10)
            
            assert len(docs) == 2
            assert docs[0]['test'] == 'doc1'


def test_get_sample_documents_empty(mock_opensearch_client):
    """Test with no documents returned."""
    mock_response = {'hits': {'hits': []}}
    
    with patch.dict('os.environ', {'OPENSEARCH_INDEX': 'test-index'}):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            client.client.search = Mock(return_value=mock_response)
            
            docs = client.get_sample_documents()
            
            assert len(docs) == 0


def test_list_indices(mock_opensearch_client):
    """Test listing indices."""
    mock_indices = {
        'user-index-1': {},
        'user-index-2': {},
        '.system-index': {}
    }
    
    with patch.dict('os.environ', {'OPENSEARCH_INDEX': 'test-index'}):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            client.client.indices.get_alias = Mock(return_value=mock_indices)
            
            indices = client.list_indices()
            
            assert len(indices) == 2
            assert 'user-index-1' in indices
            assert '.system-index' not in indices


def test_extract_fields():
    """Test field extraction from nested documents."""
    with patch.dict('os.environ', {'OPENSEARCH_INDEX': 'test-index'}):
        with patch.object(BenchmarkDataSource, '__init__', lambda x: None):
            client = BenchmarkDataSource()
            
            doc = {
                'field1': 'value1',
                'nested': {
                    'field2': 'value2'
                }
            }
            
            all_fields = set()
            field_types = {}
            field_examples = {}
            
            client._extract_fields(doc, all_fields, field_types, field_examples)
            
            assert 'field1' in all_fields
            assert 'nested' in all_fields
            assert 'nested.field2' in all_fields


def test_query_with_filters(mock_opensearch_client):
    """Test query with filters applied."""
    mock_response = {
        'hits': {
            'hits': [
                {'_source': {'test': 'filtered_doc'}}
            ]
        }
    }
    
    with patch.dict('os.environ', {'OPENSEARCH_INDEX': 'test-index'}):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            client.client.search = Mock(return_value=mock_response)
            
            filters = {'os_version': '9.5'}
            docs = client.query_with_filters(filters=filters)

            assert len(docs) == 1
            assert docs[0]['test'] == 'filtered_doc'

            # Verify search was called
            client.client.search.assert_called_once()


def test_fetch_timeseries_returns_sorted_results(mock_opensearch_client):
    """fetch_timeseries_for_document returns results sorted by metadata.sequence ascending."""
    with patch.dict('os.environ', {
        'OPENSEARCH_INDEX': 'ri',
        'OPENSEARCH_INDEX_TIMESERIES': 'tsi',
    }):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            client.client.search = Mock(
                return_value={'hits': {'hits': []}}
            )
            client.fetch_timeseries_for_document('doc-123')

            # Verify sort clause is present
            _, kwargs = client.client.search.call_args
            assert 'sort' in kwargs['body']
            assert kwargs['body']['sort'] == [{"metadata.sequence": {"order": "asc"}}]


def test_fetch_timeseries_handles_large_datasets(mock_opensearch_client):
    """fetch_timeseries_for_document can retrieve more than 100 points."""
    with patch.dict('os.environ', {
        'OPENSEARCH_INDEX': 'ri',
        'OPENSEARCH_INDEX_TIMESERIES': 'tsi',
    }):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()

            # Mock a dataset with 500 points
            mock_hits = [{'_source': {'metadata': {'sequence': i}}} for i in range(500)]
            client.client.search = Mock(
                return_value={'hits': {'hits': mock_hits}}
            )

            # Request 500 points
            rows = client.fetch_timeseries_for_document('doc-123', size=500)

            # Verify we got all 500 points
            assert len(rows) == 500

            # Verify size parameter was passed
            _, kwargs = client.client.search.call_args
            assert kwargs['body']['size'] == 500


def test_fetch_timeseries_logs_operations(mock_opensearch_client, caplog):
    """fetch_timeseries_for_document logs operation context."""
    with patch.dict('os.environ', {
        'OPENSEARCH_INDEX': 'ri',
        'OPENSEARCH_INDEX_TIMESERIES': 'tsi',
    }):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            client.client.search = Mock(
                return_value={'hits': {'hits': [
                    {'_source': {'k': 1}},
                    {'_source': {'k': 2}},
                ]}}
            )

            with caplog.at_level(logging.INFO):
                rows = client.fetch_timeseries_for_document('doc-456', size=10)

            # Verify logging occurred with context
            assert len(rows) == 2

            # Check that logs contain operation type, document_id, and result count
            log_messages = [rec.message for rec in caplog.records]

            # Should have a log entry mentioning the fetch operation
            fetch_logs = [msg for msg in log_messages if 'fetch' in msg.lower() or 'timeseries' in msg.lower()]
            assert len(fetch_logs) > 0

            # Should mention document_id
            doc_id_logs = [msg for msg in log_messages if 'doc-456' in msg]
            assert len(doc_id_logs) > 0

            # Should mention result count
            count_logs = [msg for msg in log_messages if '2' in msg or 'retrieved' in msg.lower()]
            assert len(count_logs) > 0


def test_fetch_timeseries_warns_when_hitting_size_limit(mock_opensearch_client, caplog):
    """fetch_timeseries_for_document warns when result count equals size limit."""
    with patch.dict('os.environ', {
        'OPENSEARCH_INDEX': 'ri',
        'OPENSEARCH_INDEX_TIMESERIES': 'tsi',
    }):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()

            # Mock exactly 100 results (hitting the limit)
            mock_hits = [{'_source': {'k': i}} for i in range(100)]
            client.client.search = Mock(
                return_value={'hits': {'hits': mock_hits}}
            )

            with caplog.at_level(logging.WARNING):
                rows = client.fetch_timeseries_for_document('doc-789', size=100)

            assert len(rows) == 100

            # Should warn about potential truncation
            warning_logs = [rec for rec in caplog.records if rec.levelname == 'WARNING']
            assert len(warning_logs) > 0
            assert any('limit' in rec.message.lower() or 'truncat' in rec.message.lower()
                      for rec in warning_logs)


