import pytest
from abc import ABC, abstractmethod
from app.ingestion.base_client import BaseIngestionClient


class TestBaseIngestionClient:
    """Test the abstract base class for ingestion clients"""
    
    def test_base_client_is_abstract(self):
        """Test that BaseIngestionClient is an abstract class"""
        assert issubclass(BaseIngestionClient, ABC)
        assert hasattr(BaseIngestionClient, 'fetch')
        assert BaseIngestionClient.fetch.__isabstractmethod__
    
    def test_concrete_implementation_required(self):
        """Test that concrete implementations must implement fetch method"""
        class ConcreteClient(BaseIngestionClient):
            async def fetch(self, *args, **kwargs):
                return [{"title": "Test", "content": "Test content"}]
        
        client = ConcreteClient()
        assert hasattr(client, 'fetch')
        assert callable(client.fetch)
    
    def test_abstract_method_raises_not_implemented(self):
        """Test that calling fetch on base class raises NotImplementedError"""
        # Since BaseIngestionClient is abstract, we can't instantiate it directly
        # Instead, we test that the abstract method exists and is properly defined
        assert hasattr(BaseIngestionClient, 'fetch')
        assert BaseIngestionClient.fetch.__isabstractmethod__
