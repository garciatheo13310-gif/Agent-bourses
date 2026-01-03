"""
Configuration centralisée de l'application
Toutes les constantes et paramètres de configuration
"""
import os
from typing import Optional

class Config:
    """Configuration centralisée de l'application"""
    
    # Configuration de l'application
    APP_NAME = "Agent Bourse"
    APP_VERSION = "2.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Configuration de sécurité
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_MINUTES = 15
    SESSION_TIMEOUT_MINUTES = 60
    PASSWORD_MIN_LENGTH = 6
    PASSWORD_MAX_LENGTH = 128
    
    # Configuration de rate limiting
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_WINDOW_SECONDS = 60
    
    # Configuration de cache
    CACHE_TTL_PRICES = 300  # 5 minutes
    CACHE_TTL_TICKERS = 3600  # 1 heure
    CACHE_TTL_ANALYSIS = 1800  # 30 minutes
    
    # Configuration des API
    YAHOO_FINANCE_TIMEOUT = 10
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5
    
    # Configuration de la base de données
    DB_POOL_SIZE = 5
    DB_MAX_OVERFLOW = 10
    DB_POOL_TIMEOUT = 30
    
    # Configuration des limites
    MAX_TICKERS_PER_REQUEST = 2000
    MAX_PORTFOLIO_POSITIONS = 1000
    MAX_STRING_LENGTH = 1000
    
    # Configuration des prix
    MIN_PRICE = 0.01
    MAX_PRICE = 1000000
    PRICE_VALIDATION_THRESHOLD = 0.5  # 50% d'écart max par rapport au prix d'achat
    
    # Configuration des performances
    BATCH_SIZE = 10
    BATCH_DELAY = 0.1
    SLOW_FUNCTION_THRESHOLD = 1.0  # secondes
    
    # Configuration Supabase
    SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://zypgufpilsuunsiclykw.supabase.co')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    
    # Configuration Email
    EMAIL_SENDER = os.getenv("EMAIL_USER", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASS", "")
    EMAIL_RECEIVER = os.getenv("EMAIL_TARGET", "")
    
    @staticmethod
    def validate() -> tuple[bool, Optional[str]]:
        """Valide la configuration"""
        if not Config.SUPABASE_URL:
            return False, "SUPABASE_URL non configuré"
        
        if not Config.SUPABASE_KEY:
            return False, "SUPABASE_KEY non configuré"
        
        return True, None
    
    @staticmethod
    def get_cache_key(prefix: str, *args) -> str:
        """Génère une clé de cache"""
        return f"{prefix}_{'_'.join(str(arg) for arg in args)}"

