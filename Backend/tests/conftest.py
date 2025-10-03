"""Pytest configuration and shared fixtures."""
import sys
from pathlib import Path
import pytest
import tempfile
from unittest.mock import Mock
import pandas as pd

# Ensure Backend/src is on sys.path so 'src' package resolves during tests
backend_root = Path(__file__).parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from src.core.config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return Settings(
        SECRET_KEY="test-secret-key-very-long-for-testing-purposes",
        API_KEY_BACKEND="test-api-key-backend",
        OPENAI_API_KEY="sk-test-api-key",
        DEBUG=True,
        LOG_LEVEL="DEBUG"
    )


@pytest.fixture
def temp_csv_file():
    """Create temporary CSV file for testing."""
    data = [
        "Numero de sucursal,Ingresos,Egresos,Ubicacion\n",
        "1,1000,500,Buenos Aires\n",
        "2,2000,800,CÃƒÆ’Ã‚Â³rdoba\n", 
        "3,1500,600,Rosario\n",
        "4,2500,1000,Mendoza\n"
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
        temp_file.writelines(data)
        temp_path = temp_file.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture 
def sample_dataframe():
    """Sample DataFrame for testing."""
    return pd.DataFrame({
        'Numero de sucursal': [1, 2, 3, 4],
        'Ingresos': [1000, 2000, 1500, 2500],
        'Egresos': [500, 800, 600, 1000],
        'Ubicacion': ['Buenos Aires', 'CÃƒÆ’Ã‚Â³rdoba', 'Rosario', 'Mendoza']
    })




@pytest.fixture(autouse=True)
def supply_required_settings(monkeypatch):
    """Provide baseline secrets required by Settings during tests."""
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key-very-long-for-testing-purposes')
    monkeypatch.setenv('API_KEY_BACKEND', 'test-api-key-backend')

@pytest.fixture(autouse=True)
def disable_openai_api(monkeypatch):
    """Ensure external LLM calls stay disabled during tests."""
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    
    # Mock successful validation response
    mock_validation_response = Mock()
    mock_validation_response.choices = [Mock()]
    mock_validation_response.choices[0].message.content = "Test"
    
    # Mock chat completion response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Mocked response"
    mock_response.choices[0].finish_reason = "stop"
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    
    mock_client.chat.completions.create.return_value = mock_response
    
    return mock_client


@pytest.fixture
def mock_agents():
    """Mock agent instances for testing."""
    agents = {}
    
    # Mock DataIngestionAgent
    mock_ingestion = Mock()
    mock_ingestion.handle.return_value = {
        "data": pd.DataFrame({
            'Numero de sucursal': [1, 2, 3],
            'Ingresos': [1000, 2000, 1500],
            'Egresos': [500, 800, 600]
        }),
        "summary": {"rows": 3, "columns": 3}
    }
    agents['ingestion'] = mock_ingestion
    
    # Mock AnomalyAnalysisAgent
    mock_anomaly = Mock()
    mock_anomaly_df = pd.DataFrame({
        'Numero de sucursal': [1, 3],
        'type': ['high_variance', 'outlier'],
        'severity': ['medium', 'high']
    })
    mock_anomaly.handle.return_value = {"anomalies": mock_anomaly_df}
    agents['anomaly'] = mock_anomaly
    
    # Mock DashboardAgent
    mock_dashboard = Mock()
    mock_dashboard.handle.return_value = {
        "status": "success",
        "updated": True,
        "metrics": {"total_ingresos": 4500, "total_egresos": 1900}
    }
    agents['dashboard'] = mock_dashboard
    
    return agents


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for testing."""
    return [
        {
            "role": "user",
            "content": "Ãƒâ€šÃ‚Â¿CuÃƒÆ’Ã‚Â¡ntas sucursales tenemos?",
            "timestamp": "2024-01-01T10:00:00"
        },
        {
            "role": "assistant", 
            "content": "Actualmente tenemos 4 sucursales activas en el sistema.",
            "timestamp": "2024-01-01T10:00:05"
        },
        {
            "role": "user",
            "content": "Ãƒâ€šÃ‚Â¿CuÃƒÆ’Ã‚Â¡l es el total de ingresos?",
            "timestamp": "2024-01-01T10:01:00"
        }
    ]


@pytest.fixture
def sample_anomalies():
    """Sample anomalies data for testing."""
    return [
        {
            "Numero de sucursal": 1,
            "type": "high_variance",
            "severity": "medium",
            "description": "Ingresos muy variables"
        },
        {
            "Numero de sucursal": 3,
            "type": "outlier", 
            "severity": "high",
            "description": "Valores atÃƒÆ’Ã‚Â­picos detectados"
        },
        {
            "Numero de sucursal": 2,
            "type": "trend_anomaly",
            "severity": "low", 
            "description": "Cambio de tendencia detectado"
        }
    ]


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration between tests."""
    import logging
    # Clear all handlers
    for logger in logging.Logger.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.handlers.clear()
            logger.propagate = True
    
    # Reset root logger
    logging.root.handlers.clear()
    logging.basicConfig(level=logging.INFO)


@pytest.fixture
def mock_file_config():
    """Mock file configuration for testing."""
    return {
        "available_files": [
            {
                "name": "test_data.csv",
                "path": "/test/path/test_data.csv",
                "description": "Test data file",
                "last_modified": "2024-01-01T00:00:00"
            }
        ],
        "default_file": "/test/path/test_data.csv"
    }


@pytest.fixture
def clean_environment(monkeypatch):
    """Clean environment variables for testing."""
    # Remove potentially interfering environment variables
    env_vars_to_remove = [
        'OPENAI_API_KEY',
        'GEMINI_API_KEY', 
        'API_KEY_BACKEND',
        'DATABASE_URL',
        'ENVIRONMENT',
        'SECRET_KEY'
    ]
    
    for var in env_vars_to_remove:
        monkeypatch.delenv(var, raising=False)


# Async test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
            return self
        
        def stop(self):
            self.end_time = time.time()
            return self
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Database testing fixtures  
@pytest.fixture
def mock_database():
    """Mock database for testing."""
    class MockDatabase:
        def __init__(self):
            self.data = {}
        
        def insert(self, table, data):
            if table not in self.data:
                self.data[table] = []
            self.data[table].append(data)
        
        def select(self, table, where=None):
            if table not in self.data:
                return []
            
            if where is None:
                return self.data[table]
            
            # Simple where clause matching
            results = []
            for row in self.data[table]:
                match = True
                for key, value in where.items():
                    if row.get(key) != value:
                        match = False
                        break
                if match:
                    results.append(row)
            return results
        
        def clear(self):
            self.data = {}
    
    return MockDatabase()


# Configuration for test markers
def pytest_configure(config):
    """Configure custom test markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )


