"""
Feature Flags Management for Safe Production Deployment

Provides enterprise-grade feature flag system for controlled rollout
of the semantic NLP system with instant rollback capabilities.
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
from threading import RLock

from src.core.logging import get_logger

logger = get_logger(__name__)


class FeatureFlagStatus(Enum):
    """Feature flag status levels"""
    DISABLED = "disabled"
    BETA = "beta"           # 10% rollout
    GRADUAL = "gradual"     # 50% rollout
    ENABLED = "enabled"     # 100% rollout
    FORCE_LEGACY = "force_legacy"  # Emergency fallback


@dataclass
class FeatureFlag:
    """Feature flag configuration with metadata"""
    name: str
    status: FeatureFlagStatus
    rollout_percentage: int
    description: str
    owner: str
    created_at: str
    last_modified: str
    dependencies: list[str]
    emergency_contact: str


class FeatureFlagManager:
    """
    Enterprise feature flag manager with real-time updates

    Supports:
    - Environment-based overrides
    - Percentage rollouts
    - Instant emergency rollback
    - Dependency tracking
    - Audit logging
    """

    def __init__(self):
        self._flags: Dict[str, FeatureFlag] = {}
        self._lock = RLock()
        self._session_cache: Dict[str, Dict[str, bool]] = {}

        # Initialize default flags
        self._initialize_default_flags()

        # Load from environment overrides
        self._load_environment_overrides()

        logger.info({"event": "feature_flag_manager_initialized",
                    "flags_count": len(self._flags)})

    def is_enabled(self, flag_name: str, session_id: str = "global",
                   user_context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if feature flag is enabled for given session

        Args:
            flag_name: Feature flag identifier
            session_id: User session for consistent experience
            user_context: Additional context for advanced targeting

        Returns:
            True if feature should be enabled
        """
        with self._lock:
            # Check cache for consistent session experience
            if session_id in self._session_cache and flag_name in self._session_cache[session_id]:
                cached_result = self._session_cache[session_id][flag_name]
                logger.debug({"event": "feature_flag_cache_hit",
                            "flag": flag_name, "session": session_id,
                            "result": cached_result})
                return cached_result

            # Get flag configuration
            flag = self._flags.get(flag_name)
            if not flag:
                logger.warning({"event": "feature_flag_not_found", "flag": flag_name})
                return False

            # Determine if enabled based on status
            enabled = self._evaluate_flag(flag, session_id, user_context)

            # Cache result for session consistency
            if session_id not in self._session_cache:
                self._session_cache[session_id] = {}
            self._session_cache[session_id][flag_name] = enabled

            logger.info({"event": "feature_flag_evaluated",
                        "flag": flag_name,
                        "session": session_id,
                        "status": flag.status.value,
                        "rollout_percentage": flag.rollout_percentage,
                        "result": enabled})

            return enabled

    def _evaluate_flag(self, flag: FeatureFlag, session_id: str,
                      user_context: Optional[Dict[str, Any]]) -> bool:
        """Evaluate flag based on status and rollout percentage"""

        if flag.status == FeatureFlagStatus.DISABLED:
            return False
        elif flag.status == FeatureFlagStatus.FORCE_LEGACY:
            return False
        elif flag.status == FeatureFlagStatus.ENABLED:
            return True
        elif flag.status in {FeatureFlagStatus.BETA, FeatureFlagStatus.GRADUAL}:
            # Percentage-based rollout using session hash
            session_hash = hash(session_id) % 100
            return session_hash < flag.rollout_percentage
        else:
            return False

    def update_flag(self, flag_name: str, status: FeatureFlagStatus,
                   rollout_percentage: Optional[int] = None) -> bool:
        """
        Update feature flag status (admin operation)

        Returns:
            True if update successful
        """
        with self._lock:
            if flag_name not in self._flags:
                logger.error({"event": "feature_flag_update_failed",
                            "flag": flag_name, "reason": "not_found"})
                return False

            flag = self._flags[flag_name]
            old_status = flag.status
            flag.status = status

            if rollout_percentage is not None:
                flag.rollout_percentage = rollout_percentage

            # Clear cache to apply changes immediately
            self._session_cache.clear()

            logger.warning({"event": "feature_flag_updated",
                          "flag": flag_name,
                          "old_status": old_status.value,
                          "new_status": status.value,
                          "rollout_percentage": flag.rollout_percentage,
                          "emergency_contact": flag.emergency_contact})

            return True

    def emergency_disable(self, flag_name: str, reason: str) -> bool:
        """Emergency disable with audit trail"""
        success = self.update_flag(flag_name, FeatureFlagStatus.FORCE_LEGACY)

        if success:
            logger.critical({"event": "feature_flag_emergency_disable",
                           "flag": flag_name,
                           "reason": reason,
                           "timestamp": "immediate"})

        return success

    def get_flag_status(self, flag_name: str) -> Optional[Dict[str, Any]]:
        """Get current flag configuration for monitoring"""
        with self._lock:
            flag = self._flags.get(flag_name)
            if not flag:
                return None

            return {
                "name": flag.name,
                "status": flag.status.value,
                "rollout_percentage": flag.rollout_percentage,
                "description": flag.description,
                "owner": flag.owner,
                "dependencies": flag.dependencies,
                "emergency_contact": flag.emergency_contact
            }

    def get_all_flags(self) -> Dict[str, Dict[str, Any]]:
        """Get all flags for admin dashboard"""
        with self._lock:
            return {name: self.get_flag_status(name) for name in self._flags.keys()}

    def _initialize_default_flags(self):
        """Initialize system feature flags"""
        self._flags = {
            "semantic_nlp": FeatureFlag(
                name="semantic_nlp",
                status=FeatureFlagStatus.BETA,
                rollout_percentage=20,
                description="Semantic NLP system for intent classification",
                owner="semantic-team",
                created_at="2025-01-15",
                last_modified="2025-01-15",
                dependencies=["intent_classifier", "entity_extractor"],
                emergency_contact="claude-ai@anthropic.com"
            ),
            "semantic_entity_extraction": FeatureFlag(
                name="semantic_entity_extraction",
                status=FeatureFlagStatus.GRADUAL,
                rollout_percentage=50,
                description="Enhanced entity extraction with semantic understanding",
                owner="semantic-team",
                created_at="2025-01-15",
                last_modified="2025-01-15",
                dependencies=["semantic_nlp"],
                emergency_contact="claude-ai@anthropic.com"
            ),
            "semantic_context_resolution": FeatureFlag(
                name="semantic_context_resolution",
                status=FeatureFlagStatus.ENABLED,
                rollout_percentage=100,
                description="Global conversation context management",
                owner="semantic-team",
                created_at="2025-01-15",
                last_modified="2025-01-15",
                dependencies=[],
                emergency_contact="claude-ai@anthropic.com"
            )
        }

    def _load_environment_overrides(self):
        """Load environment-based overrides for deployment flexibility"""
        # Check for environment variable overrides
        semantic_nlp_override = os.getenv('FEATURE_SEMANTIC_NLP')
        if semantic_nlp_override:
            try:
                if semantic_nlp_override.lower() == 'enabled':
                    self._flags["semantic_nlp"].status = FeatureFlagStatus.ENABLED
                    self._flags["semantic_nlp"].rollout_percentage = 100
                elif semantic_nlp_override.lower() == 'disabled':
                    self._flags["semantic_nlp"].status = FeatureFlagStatus.DISABLED
                elif semantic_nlp_override.lower() == 'force_legacy':
                    self._flags["semantic_nlp"].status = FeatureFlagStatus.FORCE_LEGACY

                logger.info({"event": "feature_flag_environment_override",
                           "flag": "semantic_nlp",
                           "override_value": semantic_nlp_override})
            except Exception as e:
                logger.error({"event": "feature_flag_environment_override_failed",
                            "flag": "semantic_nlp",
                            "error": str(e)})


# Global singleton for the application
_feature_flag_manager: Optional[FeatureFlagManager] = None


def get_feature_flag_manager() -> FeatureFlagManager:
    """Get global feature flag manager instance"""
    global _feature_flag_manager
    if _feature_flag_manager is None:
        _feature_flag_manager = FeatureFlagManager()
    return _feature_flag_manager


def is_semantic_nlp_enabled(session_id: str = "global") -> bool:
    """Convenience function for semantic NLP feature flag"""
    return get_feature_flag_manager().is_enabled("semantic_nlp", session_id)


def is_semantic_entity_extraction_enabled(session_id: str = "global") -> bool:
    """Convenience function for semantic entity extraction feature flag"""
    return get_feature_flag_manager().is_enabled("semantic_entity_extraction", session_id)


def is_semantic_context_enabled(session_id: str = "global") -> bool:
    """Convenience function for semantic context feature flag"""
    return get_feature_flag_manager().is_enabled("semantic_context_resolution", session_id)