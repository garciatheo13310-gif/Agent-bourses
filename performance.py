"""
Module d'optimisation des performances
Gère le caching, connection pooling et optimisations
"""
import functools
import time
from typing import Any, Callable, Optional
from datetime import datetime, timedelta

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

class CacheManager:
    """Gestionnaire de cache avancé pour Streamlit"""
    
    @staticmethod
    @functools.lru_cache(maxsize=128)
    def cached_function(func: Callable, *args, **kwargs):
        """Cache simple avec LRU"""
        return func(*args, **kwargs)
    
    @staticmethod
    def get_cached_data(key: str, ttl_seconds: int = 300) -> Optional[Any]:
        """Récupère des données du cache avec TTL"""
        if not STREAMLIT_AVAILABLE:
            return None
        
        if not hasattr(st, 'session_state'):
            st.session_state = {}
        if 'cache_data' not in st.session_state:
            st.session_state['cache_data'] = {}
        if 'cache_timestamps' not in st.session_state:
            st.session_state['cache_timestamps'] = {}
        
        cache_data = st.session_state['cache_data']
        cache_timestamps = st.session_state['cache_timestamps']
        
        if key in cache_data:
            timestamp = cache_timestamps.get(key, 0)
            if time.time() - timestamp < ttl_seconds:
                return cache_data[key]
            else:
                # Cache expiré, supprimer
                del cache_data[key]
                if key in cache_timestamps:
                    del cache_timestamps[key]
        
        return None
    
    @staticmethod
    def set_cached_data(key: str, value: Any, ttl_seconds: int = 300):
        """Stocke des données dans le cache avec TTL"""
        if not STREAMLIT_AVAILABLE:
            return
        
        if not hasattr(st, 'session_state'):
            st.session_state = {}
        if 'cache_data' not in st.session_state:
            st.session_state['cache_data'] = {}
        if 'cache_timestamps' not in st.session_state:
            st.session_state['cache_timestamps'] = {}
        
        st.session_state['cache_data'][key] = value
        st.session_state['cache_timestamps'][key] = time.time()
    
    @staticmethod
    def clear_cache(pattern: Optional[str] = None):
        """Nettoie le cache (optionnellement par pattern)"""
        if not STREAMLIT_AVAILABLE or not hasattr(st, 'session_state'):
            return
        
        if 'cache_data' not in st.session_state:
            return
        
        if pattern:
            keys_to_delete = [k for k in st.session_state['cache_data'].keys() if pattern in k]
            for key in keys_to_delete:
                del st.session_state['cache_data'][key]
                if key in st.session_state.get('cache_timestamps', {}):
                    del st.session_state['cache_timestamps'][key]
        else:
            st.session_state['cache_data'] = {}
            st.session_state['cache_timestamps'] = {}

class PerformanceMonitor:
    """Moniteur de performance pour identifier les goulots d'étranglement"""
    
    @staticmethod
    def time_function(func: Callable) -> Callable:
        """Décorateur pour mesurer le temps d'exécution d'une fonction"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Logger les fonctions lentes (> 1 seconde)
            if execution_time > 1.0 and STREAMLIT_AVAILABLE:
                if not hasattr(st, 'session_state'):
                    st.session_state = {}
                if 'performance_log' not in st.session_state:
                    st.session_state['performance_log'] = []
                
                st.session_state['performance_log'].append({
                    'function': func.__name__,
                    'time': execution_time,
                    'timestamp': datetime.now().isoformat()
                })
            
            return result
        return wrapper
    
    @staticmethod
    def get_performance_stats() -> dict:
        """Récupère les statistiques de performance"""
        if not STREAMLIT_AVAILABLE or not hasattr(st, 'session_state'):
            return {}
        
        if 'performance_log' not in st.session_state:
            return {}
        
        logs = st.session_state['performance_log']
        if not logs:
            return {}
        
        # Calculer les statistiques
        times = [log['time'] for log in logs]
        
        return {
            'total_calls': len(logs),
            'avg_time': sum(times) / len(times) if times else 0,
            'max_time': max(times) if times else 0,
            'min_time': min(times) if times else 0,
            'slow_functions': [log for log in logs if log['time'] > 1.0]
        }

class RequestOptimizer:
    """Optimiseur de requêtes API"""
    
    _connection_pools = {}
    
    @staticmethod
    def batch_requests(requests: list, batch_size: int = 10, delay: float = 0.1):
        """Traite les requêtes par lots pour éviter la surcharge"""
        results = []
        
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i + batch_size]
            batch_results = []
            
            for request in batch:
                try:
                    result = request()
                    batch_results.append(result)
                except Exception as e:
                    batch_results.append(None)
            
            results.extend(batch_results)
            
            # Délai entre les lots
            if i + batch_size < len(requests):
                time.sleep(delay)
        
        return results
    
    @staticmethod
    def retry_with_backoff(func: Callable, max_retries: int = 3, 
                          initial_delay: float = 0.5, backoff_factor: float = 2.0):
        """Réessaie une fonction avec backoff exponentiel"""
        delay = initial_delay
        
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                
                time.sleep(delay)
                delay *= backoff_factor
        
        return None

def optimize_dataframe(df, optimize_memory: bool = True):
    """Optimise un DataFrame pandas pour réduire la mémoire"""
    import pandas as pd
    """Optimise un DataFrame pandas pour réduire la mémoire"""
    if df is None or df.empty:
        return df
    
    if optimize_memory:
        # Convertir les types pour réduire la mémoire
        for col in df.select_dtypes(include=['int64']).columns:
            df[col] = pd.to_numeric(df[col], downcast='integer')
        
        for col in df.select_dtypes(include=['float64']).columns:
            df[col] = pd.to_numeric(df[col], downcast='float')
        
        # Convertir les strings en category si possible
        for col in df.select_dtypes(include=['object']).columns:
            if df[col].nunique() / len(df) < 0.5:  # Si moins de 50% de valeurs uniques
                df[col] = df[col].astype('category')
    
    return df

