"""Tests for configuration system."""
import pytest
from unittest.mock import patch, Mock
import os

from src.core.config import Settings, LogLevel, Environment
from src.core.exceptions import ValidationError
from pydantic import ValidationError as PydanticValidationError


class TestSettings:
    """Test settings configuration."""
    
    def test_default_values(self, clean_environment):
        """Test default configuration values."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key-very-long-for-testing-purposes',
            'API_KEY_BACKEND': 'test-api-key-backend'
        }):
            settings = Settings()
            
            assert settings.APP_NAME == "CapiAgentes API"
            assert settings.APP_VERSION == "1.0.0"
            assert settings.ENVIRONMENT == Environment.DEVELOPMENT
            assert settings.DEBUG == True
            assert settings.HOST == "0.0.0.0"
            assert settings.PORT == 8000
            assert settings.LOG_LEVEL == LogLevel.INFO
    
    def test_required_fields_validation(self, clean_environment):
        """Test validation of required fields."""
        # Missing SECRET_KEY
        with pytest.raises(PydanticValidationError):
            Settings()
        
        # SECRET_KEY too short
        with patch.dict(os.environ, {
            'SECRET_KEY': 'short',
            'API_KEY_BACKEND': 'test-api-key-backend'
        }):
            with pytest.raises(PydanticValidationError):
                Settings()
    
    def test_environment_variables_override(self, clean_environment):
        """Test environment variables override defaults."""
        env_vars = {
            'SECRET_KEY': 'test-secret-key-very-long-for-testing-purposes',
            'API_KEY_BACKEND': 'test-api-key-backend',
            'APP_NAME': 'Custom App',
            'DEBUG': 'false',
            'PORT': '9000',
            'LOG_LEVEL': 'ERROR',
            'OPENAI_API_KEY': 'sk-test-openai-key'
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.APP_NAME == 'Custom App'
            assert settings.DEBUG == False
            assert settings.PORT == 9000
            assert settings.LOG_LEVEL == LogLevel.ERROR
            assert settings.OPENAI_API_KEY == 'sk-test-openai-key'
    
    def test_cors_origins_parsing(self, clean_environment):
        """Test CORS origins string parsing."""
        env_vars = {
            'SECRET_KEY': 'test-secret-key-very-long-for-testing-purposes',
            'API_KEY_BACKEND': 'test-api-key-backend',
            'BACKEND_CORS_ORIGINS': 'http://localhost:3000,https://example.com,https://app.com'
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            expected_origins = [
                'http://localhost:3000',
                'https://example.com', 
                'https://app.com'
            ]
            assert settings.BACKEND_CORS_ORIGINS == expected_origins
    
    def test_openai_key_validation(self, clean_environment):
        """Test OpenAI API key validation."""
        base_env = {
            'SECRET_KEY': 'test-secret-key-very-long-for-testing-purposes',
            'API_KEY_BACKEND': 'test-api-key-backend'
        }
        
        # Valid OpenAI key
        with patch.dict(os.environ, {**base_env, 'OPENAI_API_KEY': 'sk-valid-key'}):
            settings = Settings()
            assert settings.OPENAI_API_KEY == 'sk-valid-key'
        
        # Invalid OpenAI key format
        with patch.dict(os.environ, {**base_env, 'OPENAI_API_KEY': 'invalid-key'}):
            with pytest.raises(PydanticValidationError):
                Settings()
    
    def test_database_url_validation(self, clean_environment):
        """Test database URL validation.""" 
        base_env = {
            'SECRET_KEY': 'test-secret-key-very-long-for-testing-purposes',
            'API_KEY_BACKEND': 'test-api-key-backend'
        }
        
        # Valid SQLite URL (default)
        with patch.dict(os.environ, base_env):
            settings = Settings()
            assert settings.DATABASE_URL.startswith('sqlite://')
        
        # Valid PostgreSQL URL
        with patch.dict(os.environ, {
            **base_env,
            'DATABASE_URL': 'postgresql://user:pass@localhost/db'
        }):
            settings = Settings()
            assert settings.DATABASE_URL == 'postgresql://user:pass@localhost/db'
        
        # Invalid database URL
        with patch.dict(os.environ, {
            **base_env,
            'DATABASE_URL': 'invalid://url'
        }):
            with pytest.raises(PydanticValidationError):
                Settings()
    
    def test_port_range_validation(self, clean_environment):
        """Test port number validation."""
        base_env = {
            'SECRET_KEY': 'test-secret-key-very-long-for-testing-purposes',
            'API_KEY_BACKEND': 'test-api-key-backend'
        }
        
        # Valid port
        with patch.dict(os.environ, {**base_env, 'PORT': '8080'}):
            settings = Settings()
            assert settings.PORT == 8080
        
        # Port too low
        with patch.dict(os.environ, {**base_env, 'PORT': '500'}):
            with pytest.raises(PydanticValidationError):
                Settings()
        
        # Port too high
        with patch.dict(os.environ, {**base_env, 'PORT': '70000'}):
            with pytest.raises(PydanticValidationError):
                Settings()
    
    def test_boolean_properties(self, clean_environment):
        """Test boolean property methods."""
        env_vars = {
            'SECRET_KEY': 'test-secret-key-very-long-for-testing-purposes',
            'API_KEY_BACKEND': 'test-api-key-backend'
        }
        
        # Development environment
        with patch.dict(os.environ, {**env_vars, 'ENVIRONMENT': 'development'}):
            settings = Settings()
            assert settings.is_development == True
            assert settings.is_production == False
        
        # Production environment
        with patch.dict(os.environ, {**env_vars, 'ENVIRONMENT': 'production'}):
            settings = Settings()
            assert settings.is_development == False
            assert settings.is_production == True
    
    def test_numeric_field_validation(self, clean_environment):
        """Test numeric field validation."""
        base_env = {
            'SECRET_KEY': 'test-secret-key-very-long-for-testing-purposes',
            'API_KEY_BACKEND': 'test-api-key-backend'
        }
        
        # Valid numeric values
        with patch.dict(os.environ, {
            **base_env,
            'WORKERS': '4',
            'RATE_LIMIT_REQUESTS': '200',
            'MAX_TOKENS': '8192',
            'TEMPERATURE': '0.8'
        }):
            settings = Settings()
            assert settings.WORKERS == 4
            assert settings.RATE_LIMIT_REQUESTS == 200
            assert settings.MAX_TOKENS == 8192
            assert settings.TEMPERATURE == 0.8
        
        # Invalid ranges
        with patch.dict(os.environ, {**base_env, 'WORKERS': '0'}):
            with pytest.raises(PydanticValidationError):
                Settings()
        
        with patch.dict(os.environ, {**base_env, 'TEMPERATURE': '3.0'}):
            with pytest.raises(PydanticValidationError):
                Settings()
    
    def test_env_file_encoding(self, clean_environment, tmp_path):
        """Test .env file encoding handling."""
        # Create test .env file with UTF-8 encoding
        env_file = tmp_path / ".env"
        env_content = """SECRET_KEY=test-secret-key-very-long-for-testing-purposes
API_KEY_BACKEND=test-api-key-backend
APP_NAME=Test App with émojis 🚀
LOG_LEVEL=INFO"""
        
        env_file.write_text(env_content, encoding='utf-8')
        
        with patch('src.core.config.Settings.Config.env_file', str(env_file)):
            settings = Settings()
            assert "émojis" in settings.APP_NAME
    
    def test_cors_origins_property(self, clean_environment):
        """Test CORS origins list property."""
        env_vars = {
            'SECRET_KEY': 'test-secret-key-very-long-for-testing-purposes',
            'API_KEY_BACKEND': 'test-api-key-backend',
            'BACKEND_CORS_ORIGINS': 'http://localhost:3000,https://example.com'
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            cors_list = settings.cors_origins_list
            assert isinstance(cors_list, list)
            assert len(cors_list) == 2
            assert 'http://localhost:3000' in cors_list
            assert 'https://example.com' in cors_list


class TestEnumValues:
    """Test enum value handling."""
    
    def test_log_level_enum(self, clean_environment):
        """Test LogLevel enum values."""
        base_env = {
            'SECRET_KEY': 'test-secret-key-very-long-for-testing-purposes',
            'API_KEY_BACKEND': 'test-api-key-backend'
        }
        
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            with patch.dict(os.environ, {**base_env, 'LOG_LEVEL': level}):
                settings = Settings()
                assert settings.LOG_LEVEL == level
        
        # Invalid log level
        with patch.dict(os.environ, {**base_env, 'LOG_LEVEL': 'INVALID'}):
            with pytest.raises(PydanticValidationError):
                Settings()
    
    def test_environment_enum(self, clean_environment):
        """Test Environment enum values."""
        base_env = {
            'SECRET_KEY': 'test-secret-key-very-long-for-testing-purposes',
            'API_KEY_BACKEND': 'test-api-key-backend'
        }
        
        for env in ['development', 'staging', 'production']:
            with patch.dict(os.environ, {**base_env, 'ENVIRONMENT': env}):
                settings = Settings()
                assert settings.ENVIRONMENT == env
        
        # Invalid environment
        with patch.dict(os.environ, {**base_env, 'ENVIRONMENT': 'invalid'}):
            with pytest.raises(PydanticValidationError):
                Settings()


class TestConfigurationIntegration:
    """Test configuration system integration."""
    
    def test_get_settings_function(self, clean_environment):
        """Test get_settings dependency injection function."""
        from src.core.config import get_settings
        
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key-very-long-for-testing-purposes',
            'API_KEY_BACKEND': 'test-api-key-backend'
        }):
            settings = get_settings()
            assert isinstance(settings, Settings)
            assert settings.APP_NAME == "CapiAgentes API"
    
    def test_settings_singleton_behavior(self, clean_environment):
        """Test that settings behave as expected for dependency injection."""
        from src.core.config import get_settings
        
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key-very-long-for-testing-purposes',
            'API_KEY_BACKEND': 'test-api-key-backend'
        }):
            settings1 = get_settings()
            settings2 = get_settings()
            
            # Should be the same instance due to module-level instantiation
            assert settings1 is settings2
    
    @pytest.mark.integration
    def test_configuration_with_real_env_file(self, tmp_path):
        """Integration test with real .env file."""
        # Create a real .env file
        env_file = tmp_path / ".env"
        env_content = """SECRET_KEY=integration-test-secret-key-very-long-for-testing
API_KEY_BACKEND=integration-test-api-key-backend
OPENAI_API_KEY=sk-integration-test-openai-key
APP_NAME=Integration Test App
DEBUG=true
LOG_LEVEL=DEBUG
PORT=8080
ENVIRONMENT=development
RATE_LIMIT_REQUESTS=50
BACKEND_CORS_ORIGINS=http://localhost:3000,https://test.com"""
        
        env_file.write_text(env_content, encoding='utf-8')
        
        # Mock the env_file path
        with patch('src.core.config.Settings.Config.env_file', str(env_file)):
            settings = Settings()
            
            # Verify all values were loaded correctly
            assert settings.SECRET_KEY == 'integration-test-secret-key-very-long-for-testing'
            assert settings.API_KEY_BACKEND == 'integration-test-api-key-backend'
            assert settings.OPENAI_API_KEY == 'sk-integration-test-openai-key'
            assert settings.APP_NAME == 'Integration Test App'
            assert settings.DEBUG == True
            assert settings.LOG_LEVEL == LogLevel.DEBUG
            assert settings.PORT == 8080
            assert settings.ENVIRONMENT == Environment.DEVELOPMENT
            assert settings.RATE_LIMIT_REQUESTS == 50
            assert len(settings.BACKEND_CORS_ORIGINS) == 2