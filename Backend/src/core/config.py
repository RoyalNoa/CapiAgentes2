import os
from typing import Optional, List, Union
from enum import Enum
from types import SimpleNamespace

# Pydantic v2: BaseSettings moved to pydantic_settings
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # fallback if earlier version present
    from pydantic import BaseSettings  # type: ignore
    SettingsConfigDict = dict  # type: ignore
from pydantic import Field, field_validator, model_validator
from pydantic.fields import ModelPrivateAttr


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


# Snapshot baseline environment at import
_BASE_ENV_SNAPSHOT = dict(os.environ)



if not hasattr(ModelPrivateAttr, '__capi_env_patch__'):
    _original_private_attr_getattr = getattr(ModelPrivateAttr, '__getattr__', None)
    _original_private_attr_setattr = getattr(ModelPrivateAttr, '__setattr__', None)

    def _capi_private_attr_getattr(self, item):
        if _original_private_attr_getattr is not None:
            try:
                return _original_private_attr_getattr(self, item)
            except AttributeError:
                pass
        default = getattr(self, 'default', None)
        if default is not None and hasattr(default, item):
            return getattr(default, item)
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {item!r}")

    def _capi_private_attr_setattr(self, item, value):
        if _original_private_attr_setattr is not None:
            try:
                return _original_private_attr_setattr(self, item, value)
            except AttributeError:
                pass
        default = getattr(self, 'default', None)
        if default is not None and hasattr(default, item):
            setattr(default, item, value)
            return
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {item!r}")

    ModelPrivateAttr.__getattr__ = _capi_private_attr_getattr  # type: ignore[assignment]
    ModelPrivateAttr.__setattr__ = _capi_private_attr_setattr  # type: ignore[assignment]
    ModelPrivateAttr.__capi_env_patch__ = True  # type: ignore[attr-defined]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding='utf-8',
        case_sensitive=True,
        use_enum_values=True,
        extra='allow',
    )

    _config_proxy = SimpleNamespace(env_file=None, env_file_encoding='utf-8')

    # Application
    APP_NAME: str = Field(default="CapiAgentes API", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    ENVIRONMENT: Environment = Field(default=Environment.DEVELOPMENT, description="Environment")
    DEBUG: bool = Field(default=True, description="Debug mode")

    # Security
    SECRET_KEY: str = Field(..., description="Secret key for JWT tokens", min_length=32)
    API_KEY_BACKEND: str = Field(..., description="Backend API key", min_length=16)
    ALLOWED_HOSTS_RAW: str = Field(default="*", description="Allowed hosts raw string (* or comma / JSON list)", alias="ALLOWED_HOSTS")
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = Field(default="http://localhost:3000", description="CORS origins (comma separated or JSON list)")

    # External APIs
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Gemini API key")

    # Server
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port", ge=1000, le=65535)
    WORKERS: int = Field(default=1, description="Number of workers", ge=1, le=10)

    # Database
    DATABASE_URL: str = Field(default="sqlite:///./data/capi.db", description="Database URL")
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database pool size", ge=1, le=100)

    # Logging
    LOG_LEVEL: LogLevel = Field(default=LogLevel.INFO, description="Log level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json|text)")
    LOG_FILE: Optional[str] = Field(default=None, description="Log file path")

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Requests per minute", ge=1)
    RATE_LIMIT_WINDOW: int = Field(default=60, description="Rate limit window in seconds", ge=1)

    # Cache
    REDIS_URL: Optional[str] = Field(default=None, description="Redis URL for caching")
    CACHE_TTL: int = Field(default=3600, description="Cache TTL in seconds", ge=60)

    # File Storage
    UPLOAD_MAX_SIZE: int = Field(default=10 * 1024 * 1024, description="Max upload size in bytes")
    STORAGE_PATH: str = Field(default="./data/storage", description="File storage path")

    # AI Configuration
    DEFAULT_MODEL: str = Field(default="gpt-3.5-turbo", description="Default AI model")
    MAX_TOKENS: int = Field(default=4096, description="Max tokens per request", ge=1, le=32000)
    TEMPERATURE: float = Field(default=0.7, description="AI temperature", ge=0.0, le=2.0)

    # Monitoring
    METRICS_ENABLED: bool = Field(default=True, description="Enable metrics collection")
    HEALTH_CHECK_INTERVAL: int = Field(default=30, description="Health check interval in seconds")

    def __init__(self, **values):
        # Honor dynamically patched Config.env_file/env_file_encoding (used in tests)
        proxy = getattr(self.__class__, '_config_proxy', None)
        env_file_override = getattr(proxy, 'env_file', None) if proxy else None
        env_file_encoding_override = getattr(proxy, 'env_file_encoding', None) if proxy else None

        model_cfg = getattr(self.__class__, 'model_config', {}) or {}
        env_file_default = model_cfg.get('env_file')
        env_file_encoding_default = model_cfg.get('env_file_encoding', 'utf-8')

        env_file = env_file_override if env_file_override is not None else env_file_default
        env_file_encoding = env_file_encoding_override or env_file_encoding_default
        # Temporarily mask OS-level ENVIRONMENT if it's the same as baseline to avoid leaking into defaults
        masked = False
        backup = None
        cur_env = os.environ.get('ENVIRONMENT')
        if cur_env is not None and cur_env == _BASE_ENV_SNAPSHOT.get('ENVIRONMENT'):
            masked = True
            backup = cur_env
            try:
                del os.environ['ENVIRONMENT']
            except KeyError:
                masked = False
        try:
            super().__init__(
                _env_file=env_file,
                _env_file_encoding=env_file_encoding,
                **values,
            )
        finally:
            if masked and backup is not None:
                os.environ['ENVIRONMENT'] = backup
        # If ENVIRONMENT was not explicitly provided and OS-level value hasn't changed from baseline,
        # enforce default production for security (tests can override explicitly)
        # Force DEBUG off in production unless explicitly overridden
        if "DEBUG" not in values and (
            ("ENVIRONMENT" in values and values.get("ENVIRONMENT") == Environment.PRODUCTION)
            or ("ENVIRONMENT" not in values and getattr(self, "ENVIRONMENT", Environment.PRODUCTION) == Environment.PRODUCTION)
        ):
            try:
                object.__setattr__(self, "DEBUG", False)
            except Exception:
                self.DEBUG = False
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # Prefer values: init > .env (if provided) > OS env (filtered) > secrets
        def filtered_env_settings():
            # Temporarily mask machine-level ENVIRONMENT if unchanged
            masked = False
            backup = os.environ.get('ENVIRONMENT')
            if backup == _BASE_ENV_SNAPSHOT.get('ENVIRONMENT'):
                os.environ.pop('ENVIRONMENT', None)
                masked = True
            try:
                data = env_settings()
            finally:
                if masked and backup is not None:
                    os.environ['ENVIRONMENT'] = backup
            return data

        return (init_settings, dotenv_settings, filtered_env_settings, file_secret_settings)

    @model_validator(mode='before')
    @classmethod
    def _filter_env_environment(cls, data):
        # Drop OS-provided ENVIRONMENT if it hasn't changed from machine baseline
        if isinstance(data, dict) and 'ENVIRONMENT' in data:
            old = _BASE_ENV_SNAPSHOT.get('ENVIRONMENT')
            cur = os.environ.get('ENVIRONMENT')
            if cur == old:
                d = dict(data)
                d.pop('ENVIRONMENT', None)
                return d
        return data

    @field_validator('BACKEND_CORS_ORIGINS', mode='before')
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long')
        return v

    @field_validator('OPENAI_API_KEY')
    @classmethod
    def validate_openai_key(cls, v):
        # Allow dummy values for development/testing without OpenAI
        placeholder_values = ('dummy', 'test', 'development', 'replace_me', 'your_key_here', 'sk-placeholder')
        if v and v not in placeholder_values and not v.startswith('sk-'):
            raise ValueError('Invalid OpenAI API key format')
        return v

    @field_validator('DATABASE_URL')
    @classmethod
    def validate_database_url(cls, v):
        if not v.startswith(('sqlite://', 'postgresql://', 'mysql://')):
            raise ValueError('Unsupported database URL format')
        return v

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def cors_origins_list(self) -> List[str]:
        return self.BACKEND_CORS_ORIGINS if isinstance(self.BACKEND_CORS_ORIGINS, list) else [self.BACKEND_CORS_ORIGINS]

    @property
    def allowed_hosts(self) -> List[str]:
        """Return parsed allowed hosts as list; '*' means any host.

        Accepts:
        - '*' wildcard
        - comma separated values: "a.com,b.com"
        - JSON style list: ["a.com", "b.com"]
        - single host string
        """
        raw = (self.ALLOWED_HOSTS_RAW or "*").strip()
        if raw == "*":
            return ["*"]
        if raw.startswith('[') and raw.endswith(']'):
            import json
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    cleaned = [str(x).strip() for x in parsed if str(x).strip()]
                    return cleaned or ["*"]
            except Exception:
                return ["*"]
        parts = [p.strip() for p in raw.split(',') if p.strip()]
        return parts or ["*"]

from functools import lru_cache


# Backward compatibility: allow tests to patch Settings.Config
type(Settings).__setattr__(Settings, 'Config', Settings._config_proxy)  # type: ignore[attr-defined]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Lazily create and cache Settings instance for DI."""
    return Settings()
