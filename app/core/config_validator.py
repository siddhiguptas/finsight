"""
Configuration Validation Utility

This module provides validation for all application configuration settings
to ensure the system can operate correctly.
"""

import logging
from typing import Dict, List, Tuple, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class ConfigValidator:
    """Validates application configuration settings."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_all(self) -> Dict[str, Any]:
        """Validate all configuration settings."""
        logger.info("Starting configuration validation...")
        
        # Validate database settings
        self._validate_database_config()
        
        # Validate Redis settings
        self._validate_redis_config()
        
        # Validate external API credentials
        self._validate_api_credentials()
        
        # Validate Celery settings
        self._validate_celery_config()
        
        # Validate logging settings
        self._validate_logging_config()
        
        # Generate validation report
        report = {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": self._generate_summary()
        }
        
        if report["valid"]:
            logger.info("Configuration validation completed successfully")
        else:
            logger.error(f"Configuration validation failed with {len(self.errors)} errors")
        
        return report
    
    def _validate_database_config(self):
        """Validate database configuration."""
        # Check PostgreSQL settings
        if not settings.database_url:
            self.errors.append("PostgreSQL database_url is not configured")
        
        if not settings.async_database_url:
            self.errors.append("PostgreSQL async_database_url is not configured")
        
        # Check MongoDB settings
        if not settings.mongodb_url:
            self.errors.append("MongoDB mongodb_url is not configured")
        
        if not settings.mongodb_name:
            self.errors.append("MongoDB mongodb_name is not configured")
    
    def _validate_redis_config(self):
        """Validate Redis configuration."""
        if not settings.redis_url:
            self.errors.append("Redis redis_url is not configured")
    
    def _validate_api_credentials(self):
        """Validate external API credentials."""
        # NewsAPI
        if not settings.newsapi_key:
            self.warnings.append("NewsAPI key not configured - NewsAPI client will be disabled")
        
        # Reddit
        if not all([settings.reddit_client_id, settings.reddit_client_secret]):
            self.warnings.append("Reddit API credentials incomplete - Reddit client will be disabled")
        
        # Alpha Vantage
        if not settings.alpha_vantage_api_key:
            self.warnings.append("Alpha Vantage API key not configured - Alpha Vantage client will be disabled")
        
        # SEC EDGAR
        if not settings.sec_edgar_user_agent:
            self.warnings.append("SEC EDGAR user agent not configured - SEC EDGAR client may have issues")
    
    def _validate_celery_config(self):
        """Validate Celery configuration."""
        if not settings.celery_broker_url:
            self.errors.append("Celery broker_url is not configured")
        
        if not settings.celery_result_backend:
            self.errors.append("Celery result_backend is not configured")
    
    def _validate_logging_config(self):
        """Validate logging configuration."""
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        
        if settings.log_level not in valid_log_levels:
            self.errors.append(f"Invalid log_level: {settings.log_level}. Must be one of {valid_log_levels}")
    
    def _generate_summary(self) -> str:
        """Generate a summary of validation results."""
        error_count = len(self.errors)
        warning_count = len(self.warnings)
        
        if error_count == 0 and warning_count == 0:
            return "All configuration settings are valid"
        elif error_count == 0:
            return f"Configuration valid with {warning_count} warnings"
        else:
            return f"Configuration has {error_count} errors and {warning_count} warnings"
    
    def print_report(self):
        """Print validation report to console."""
        report = self.validate_all()
        
        print("\n" + "="*60)
        print("CONFIGURATION VALIDATION REPORT")
        print("="*60)
        
        if report["valid"]:
            print("✅ Configuration is VALID")
        else:
            print("❌ Configuration has ERRORS")
        
        print(f"\nSummary: {report['summary']}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        print("\n" + "="*60)
        
        return report

def validate_configuration() -> Dict[str, Any]:
    """Convenience function to validate configuration."""
    validator = ConfigValidator()
    return validator.validate_all()

def validate_and_exit_if_invalid():
    """Validate configuration and exit if invalid."""
    validator = ConfigValidator()
    report = validator.validate_all()
    
    if not report["valid"]:
        print("Configuration validation failed. Please fix the errors above.")
        exit(1)
    
    return report