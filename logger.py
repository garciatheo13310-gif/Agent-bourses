"""
Module de logging professionnel
Gère les logs structurés avec différents niveaux
"""
import logging
import sys
from datetime import datetime
from typing import Optional
import os

class AppLogger:
    """Logger professionnel pour l'application"""
    
    _logger: Optional[logging.Logger] = None
    
    @staticmethod
    def get_logger(name: str = "agent_bourse") -> logging.Logger:
        """Obtient ou crée un logger"""
        if AppLogger._logger is None:
            AppLogger._logger = logging.getLogger(name)
            AppLogger._logger.setLevel(logging.INFO)
            
            # Éviter les doublons de handlers
            if not AppLogger._logger.handlers:
                # Handler pour la console
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(logging.INFO)
                
                # Format des logs
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                console_handler.setFormatter(formatter)
                
                AppLogger._logger.addHandler(console_handler)
                
                # Handler pour fichier (optionnel)
                log_dir = os.path.join(os.path.dirname(__file__), 'logs')
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)
                
                file_handler = logging.FileHandler(
                    os.path.join(log_dir, 'app.log'),
                    encoding='utf-8'
                )
                file_handler.setLevel(logging.WARNING)
                file_handler.setFormatter(formatter)
                AppLogger._logger.addHandler(file_handler)
        
        return AppLogger._logger
    
    @staticmethod
    def info(message: str, **kwargs):
        """Log un message d'information"""
        logger = AppLogger.get_logger()
        logger.info(message, extra=kwargs)
    
    @staticmethod
    def warning(message: str, **kwargs):
        """Log un avertissement"""
        logger = AppLogger.get_logger()
        logger.warning(message, extra=kwargs)
    
    @staticmethod
    def error(message: str, exception: Optional[Exception] = None, **kwargs):
        """Log une erreur"""
        logger = AppLogger.get_logger()
        if exception:
            logger.error(f"{message}: {str(exception)}", exc_info=True, extra=kwargs)
        else:
            logger.error(message, extra=kwargs)
    
    @staticmethod
    def debug(message: str, **kwargs):
        """Log un message de debug"""
        logger = AppLogger.get_logger()
        logger.debug(message, extra=kwargs)
    
    @staticmethod
    def security_event(event_type: str, user_id: Optional[str] = None, 
                      details: Optional[dict] = None):
        """Log un événement de sécurité"""
        logger = AppLogger.get_logger()
        log_data = {
            'event_type': event_type,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        logger.warning(f"SECURITY_EVENT: {log_data}")

