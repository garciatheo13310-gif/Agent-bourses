"""
Module de sécurité professionnel pour Agent Bourse
Gère la validation, sanitization et protection des données
"""
import re
import html
from typing import Optional, Any
from datetime import datetime

# Import optionnel de streamlit
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    # Créer un mock pour les tests
    class MockStreamlit:
        session_state = {}
    st = MockStreamlit()

class SecurityValidator:
    """Classe pour valider et sécuriser les entrées utilisateur"""
    
    # Patterns de validation
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,20}$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    TICKER_PATTERN = re.compile(r'^[A-Z0-9._-]{1,20}$')
    ISIN_PATTERN = re.compile(r'^[A-Z]{2}[A-Z0-9]{9}\d$')
    
    # Limites de sécurité
    MAX_STRING_LENGTH = 1000
    MAX_NUMBER_VALUE = 1e15
    MIN_NUMBER_VALUE = -1e15
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = MAX_STRING_LENGTH) -> str:
        """Nettoie et sécurise une chaîne de caractères"""
        if not isinstance(value, str):
            return ""
        
        # Limiter la longueur
        value = value[:max_length]
        
        # Échapper les caractères HTML
        value = html.escape(value)
        
        # Supprimer les caractères de contrôle
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
        
        return value.strip()
    
    @staticmethod
    def validate_username(username: str):
        """Valide un nom d'utilisateur"""
        if not username:
            return False, "Le nom d'utilisateur est requis"
        
        if not isinstance(username, str):
            return False, "Le nom d'utilisateur doit être une chaîne de caractères"
        
        if len(username) < 3:
            return False, "Le nom d'utilisateur doit contenir au moins 3 caractères"
        
        if len(username) > 20:
            return False, "Le nom d'utilisateur ne peut pas dépasser 20 caractères"
        
        if not SecurityValidator.USERNAME_PATTERN.match(username):
            return False, "Le nom d'utilisateur ne peut contenir que des lettres, chiffres et underscores"
        
        return True, None
    
    @staticmethod
    def validate_email(email: str):
        """Valide un email"""
        if not email:
            return False, "L'email est requis"
        
        if not isinstance(email, str):
            return False, "L'email doit être une chaîne de caractères"
        
        if len(email) > 255:
            return False, "L'email est trop long"
        
        if not SecurityValidator.EMAIL_PATTERN.match(email):
            return False, "Format d'email invalide"
        
        return True, None
    
    @staticmethod
    def validate_password(password: str):
        """Valide un mot de passe"""
        if not password:
            return False, "Le mot de passe est requis"
        
        if len(password) < 6:
            return False, "Le mot de passe doit contenir au moins 6 caractères"
        
        if len(password) > 128:
            return False, "Le mot de passe est trop long"
        
        return True, None
    
    @staticmethod
    def validate_ticker(ticker: str):
        """Valide un symbole boursier (ticker)"""
        if not ticker:
            return False, "Le symbole est requis"
        
        ticker = ticker.upper().strip()
        
        # Vérifier le format
        if not SecurityValidator.TICKER_PATTERN.match(ticker):
            return False, "Format de symbole invalide"
        
        return True, None
    
    @staticmethod
    def validate_isin(isin: str):
        """Valide un code ISIN"""
        if not isin:
            return False, "Le code ISIN est requis"
        
        isin = isin.upper().strip()
        
        if not SecurityValidator.ISIN_PATTERN.match(isin):
            return False, "Format de code ISIN invalide"
        
        return True, None
    
    @staticmethod
    def validate_number(value: Any, min_val: float = None, max_val: float = None):
        """Valide un nombre"""
        try:
            num = float(value)
            
            if min_val is not None and num < min_val:
                return False, f"La valeur doit être supérieure ou égale à {min_val}"
            
            if max_val is not None and num > max_val:
                return False, f"La valeur doit être inférieure ou égale à {max_val}"
            
            if num < SecurityValidator.MIN_NUMBER_VALUE or num > SecurityValidator.MAX_NUMBER_VALUE:
                return False, "La valeur est hors limites"
            
            return True, None
        except (ValueError, TypeError):
            return False, "La valeur doit être un nombre"
    
    @staticmethod
    def validate_quantity(quantity: Any):
        """Valide une quantité d'actions"""
        return SecurityValidator.validate_number(quantity, min_val=0.0001, max_val=1e10)
    
    @staticmethod
    def validate_price(price: Any):
        """Valide un prix"""
        return SecurityValidator.validate_number(price, min_val=0.01, max_val=1e6)
    
    @staticmethod
    def validate_date(date_str: str):
        """Valide une date"""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True, None
        except ValueError:
            return False, "Format de date invalide (attendu: YYYY-MM-DD)"
    
    @staticmethod
    def sanitize_portfolio_data(data: dict) -> dict:
        """Nettoie et valide les données d'un portefeuille"""
        sanitized = {}
        
        allowed_keys = ['symbol', 'name', 'quantite', 'prix_achat', 'date_achat', 
                       'prix_actuel_manuel', 'compte_type']
        
        for key, value in data.items():
            if key not in allowed_keys:
                continue
            
            if isinstance(value, str):
                sanitized[key] = SecurityValidator.sanitize_string(value, max_length=100)
            elif isinstance(value, (int, float)):
                sanitized[key] = value
            else:
                sanitized[key] = value
        
        return sanitized

class RateLimiter:
    """Gestion du rate limiting pour protéger contre les abus"""
    
    @staticmethod
    def check_rate_limit(user_id: Optional[str], action: str, max_requests: int = 10, 
                        window_seconds: int = 60) -> bool:
        """Vérifie si l'utilisateur a dépassé la limite de requêtes"""
        if not STREAMLIT_AVAILABLE:
            return False  # Pas de rate limiting si Streamlit n'est pas disponible
        
        cache_key = f"rate_limit_{user_id}_{action}"
        
        if not hasattr(st, 'session_state') or cache_key not in st.session_state:
            if not hasattr(st, 'session_state'):
                st.session_state = {}
            st.session_state[cache_key] = {
                'count': 0,
                'reset_time': datetime.now().timestamp() + window_seconds
            }
        
        rate_data = st.session_state[cache_key]
        
        # Réinitialiser si la fenêtre est expirée
        if datetime.now().timestamp() > rate_data['reset_time']:
            rate_data['count'] = 0
            rate_data['reset_time'] = datetime.now().timestamp() + window_seconds
        
        # Vérifier la limite
        if rate_data['count'] >= max_requests:
            return True  # Limite dépassée
        
        # Incrémenter le compteur
        rate_data['count'] += 1
        return False  # Dans les limites

class InputSanitizer:
    """Classe pour nettoyer les entrées utilisateur"""
    
    @staticmethod
    def sanitize_input(value: Any, input_type: str = 'string') -> Any:
        """Nettoie une entrée selon son type"""
        if value is None:
            return None
        
        if input_type == 'string':
            return SecurityValidator.sanitize_string(str(value))
        elif input_type == 'number':
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        elif input_type == 'integer':
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
        elif input_type == 'ticker':
            value = str(value).upper().strip()
            if SecurityValidator.validate_ticker(value)[0]:
                return value
            return None
        elif input_type == 'email':
            value = str(value).lower().strip()
            if SecurityValidator.validate_email(value)[0]:
                return value
            return None
        
        return value

