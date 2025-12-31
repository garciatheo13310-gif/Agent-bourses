"""
Module de gestion de la base de données pour l'application Agent Bourse
Version API Supabase - Plus simple et plus fiable que PostgreSQL direct
"""
import json
import bcrypt
import re
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List

# Essayer d'importer le client Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️ supabase-py non disponible, utilisation de SQLite")

# Récupérer les credentials Supabase depuis les variables d'environnement
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://zypgufpilsuunsiclykw.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'sb_publishable_tuyj9qXdFw5SnVVUMKAGdw_1mDDyf27')

# Client Supabase global
_supabase_client: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    """Obtient le client Supabase"""
    global _supabase_client
    if _supabase_client is None and SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY:
        try:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            # Test de connexion
            _supabase_client.table('users').select('id').limit(1).execute()
            return _supabase_client
        except Exception as e:
            print(f"⚠️ Erreur connexion Supabase: {str(e)[:100]}")
            return None
    return _supabase_client

def is_using_supabase() -> bool:
    """Vérifie si Supabase est disponible et fonctionne"""
    if not SUPABASE_AVAILABLE:
        return False
    client = get_supabase_client()
    return client is not None

# Fallback SQLite
import sqlite3

def get_sqlite_connection():
    """Obtient une connexion SQLite (fallback)"""
    DB_PATH = os.path.join(os.path.dirname(__file__), 'agent_bourse.db')
    return sqlite3.connect(DB_PATH)

def init_database():
    """Initialise la base de données avec les tables nécessaires"""
    if is_using_supabase():
        # Les tables sont créées automatiquement par Supabase
        # On vérifie juste qu'elles existent
        try:
            client = get_supabase_client()
            # Test de connexion en vérifiant la table users
            client.table('users').select('id').limit(1).execute()
            print("✅ Supabase connecté et prêt")
        except Exception as e:
            print(f"⚠️ Erreur initialisation Supabase: {e}")
            # Créer les tables en SQLite en fallback
            init_sqlite_tables()
    else:
        init_sqlite_tables()

def init_sqlite_tables():
    """Initialise les tables SQLite (fallback)"""
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            pea TEXT DEFAULT '[]',
            compte_titre TEXT DEFAULT '[]',
            crypto_kraken TEXT DEFAULT '[]',
            comptes_bancaires TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            analysis_data TEXT NOT NULL,
            scan_date VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rate_limiting (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ip_address VARCHAR(50),
            action VARCHAR(50),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Vérifie un mot de passe"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except:
        return False

def is_valid_email(email: str) -> bool:
    """Valide un email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_username(username: str) -> bool:
    """Valide un nom d'utilisateur"""
    return re.match(r'^[a-zA-Z0-9_]{3,20}$', username) is not None

def create_user(username: str, email: str, password: str) -> Optional[int]:
    """Crée un nouvel utilisateur"""
    if not is_valid_email(email) or not is_valid_username(username) or len(password) < 6:
        return None
    
    try:
        if is_using_supabase():
            client = get_supabase_client()
            password_hash = hash_password(password)
            
            # Vérifier si l'utilisateur existe déjà
            existing = client.table('users').select('id').eq('username', username).execute()
            if existing.data:
                return None
            
            existing_email = client.table('users').select('id').eq('email', email).execute()
            if existing_email.data:
                return None
            
            # Créer l'utilisateur
            result = client.table('users').insert({
                'username': username,
                'email': email,
                'password_hash': password_hash
            }).execute()
            
            if result.data:
                user_id = result.data[0]['id']
                # Créer un portefeuille vide
                client.table('portfolios').insert({
                    'user_id': user_id,
                    'pea': '[]',
                    'compte_titre': '[]',
                    'crypto_kraken': '[]',
                    'comptes_bancaires': '[]'
                }).execute()
                return user_id
        else:
            # Fallback SQLite
            conn = get_sqlite_connection()
            cursor = conn.cursor()
            
            # Vérifier si existe
            cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
            if cursor.fetchone():
                conn.close()
                return None
            
            password_hash = hash_password(password)
            cursor.execute('''
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
            ''', (username, email, password_hash))
            user_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO portfolios (user_id, pea, compte_titre, crypto_kraken, comptes_bancaires)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, '[]', '[]', '[]', '[]'))
            
            conn.commit()
            conn.close()
            return user_id
    except Exception as e:
        print(f"Erreur création utilisateur: {e}")
        return None

def verify_user(username: str, password: str, ip_address: str = None) -> Optional[int]:
    """Vérifie les identifiants"""
    try:
        if is_using_supabase():
            client = get_supabase_client()
            
            # Récupérer l'utilisateur
            result = client.table('users').select('*').eq('username', username).execute()
            
            if not result.data:
                return None
            
            user = result.data[0]
            user_id = user['id']
            stored_hash = user['password_hash']
            failed_attempts = user.get('failed_login_attempts', 0) or 0
            locked_until = user.get('locked_until')
            
            # Vérifier si bloqué
            if locked_until:
                try:
                    locked_until_dt = datetime.fromisoformat(locked_until.replace('Z', '+00:00'))
                    if datetime.now(locked_until_dt.tzinfo) < locked_until_dt:
                        remaining = int((locked_until_dt - datetime.now(locked_until_dt.tzinfo)).total_seconds() / 60)
                        raise Exception(f"Compte bloqué. Réessayez dans {remaining} minutes.")
                except:
                    pass
            
            # Vérifier le mot de passe
            if verify_password(password, stored_hash):
                # Connexion réussie
                client.table('users').update({
                    'last_login': datetime.now().isoformat(),
                    'failed_login_attempts': 0,
                    'locked_until': None
                }).eq('id', user_id).execute()
                return user_id
            else:
                # Échec - incrémenter tentatives
                failed_attempts = failed_attempts + 1
                
                if failed_attempts >= 5:
                    locked_until = (datetime.now() + timedelta(minutes=30)).isoformat()
                    client.table('users').update({
                        'failed_login_attempts': failed_attempts,
                        'locked_until': locked_until
                    }).eq('id', user_id).execute()
                else:
                    client.table('users').update({
                        'failed_login_attempts': failed_attempts
                    }).eq('id', user_id).execute()
                
                remaining_attempts = 5 - failed_attempts
                if remaining_attempts > 0:
                    raise Exception(f"Mot de passe incorrect. {remaining_attempts} tentative(s) restante(s).")
                else:
                    raise Exception("Trop de tentatives échouées. Compte bloqué pendant 30 minutes.")
        else:
            # Fallback SQLite
            conn = get_sqlite_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, password_hash, failed_login_attempts, locked_until
                FROM users WHERE username = ?
            ''', (username,))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return None
            
            user_id, stored_hash, failed_attempts, locked_until = result
            
            # Vérifier si bloqué
            if locked_until:
                try:
                    locked_until_dt = datetime.fromisoformat(locked_until)
                    if datetime.now() < locked_until_dt:
                        remaining = int((locked_until_dt - datetime.now()).total_seconds() / 60)
                        conn.close()
                        raise Exception(f"Compte bloqué. Réessayez dans {remaining} minutes.")
                except:
                    pass
            
            # Vérifier le mot de passe
            if verify_password(password, stored_hash):
                cursor.execute('''
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP,
                        failed_login_attempts = 0,
                        locked_until = NULL
                    WHERE id = ?
                ''', (user_id,))
                conn.commit()
                conn.close()
                return user_id
            else:
                failed_attempts = (failed_attempts or 0) + 1
                
                if failed_attempts >= 5:
                    locked_until = (datetime.now() + timedelta(minutes=30)).isoformat()
                    cursor.execute('''
                        UPDATE users 
                        SET failed_login_attempts = ?, locked_until = ?
                        WHERE id = ?
                    ''', (failed_attempts, locked_until, user_id))
                else:
                    cursor.execute('''
                        UPDATE users SET failed_login_attempts = ? WHERE id = ?
                    ''', (failed_attempts, user_id))
                
                conn.commit()
                conn.close()
                
                remaining_attempts = 5 - failed_attempts
                if remaining_attempts > 0:
                    raise Exception(f"Mot de passe incorrect. {remaining_attempts} tentative(s) restante(s).")
                else:
                    raise Exception("Trop de tentatives échouées. Compte bloqué pendant 30 minutes.")
    except Exception as e:
        if isinstance(e, Exception) and ("bloqué" in str(e) or "incorrect" in str(e)):
            raise
        print(f"Erreur vérification utilisateur: {e}")
        return None

def user_exists(username: str) -> bool:
    """Vérifie si un utilisateur existe"""
    try:
        if is_using_supabase():
            client = get_supabase_client()
            result = client.table('users').select('id').eq('username', username).execute()
            return len(result.data) > 0
        else:
            conn = get_sqlite_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
            conn.close()
            return result is not None
    except:
        return False

def email_exists(email: str) -> bool:
    """Vérifie si un email existe"""
    try:
        if is_using_supabase():
            client = get_supabase_client()
            result = client.table('users').select('id').eq('email', email).execute()
            return len(result.data) > 0
        else:
            conn = get_sqlite_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            result = cursor.fetchone()
            conn.close()
            return result is not None
    except:
        return False

def get_user_email(user_id: int) -> Optional[str]:
    """Récupère l'email d'un utilisateur"""
    try:
        if is_using_supabase():
            client = get_supabase_client()
            result = client.table('users').select('email').eq('id', user_id).execute()
            if result.data:
                return result.data[0]['email']
        else:
            conn = get_sqlite_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT email FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            if result:
                return result[0]
    except:
        pass
    return None

def get_user_portfolio(user_id: int) -> Dict:
    """Récupère le portefeuille d'un utilisateur"""
    try:
        if is_using_supabase():
            client = get_supabase_client()
            result = client.table('portfolios').select('*').eq('user_id', user_id).execute()
            
            if result.data:
                portfolio = result.data[0]
                return {
                    'pea': json.loads(portfolio.get('pea', '[]')),
                    'compte_titre': json.loads(portfolio.get('compte_titre', '[]')),
                    'crypto_kraken': json.loads(portfolio.get('crypto_kraken', '[]')),
                    'comptes_bancaires': json.loads(portfolio.get('comptes_bancaires', '[]'))
                }
        else:
            conn = get_sqlite_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pea, compte_titre, crypto_kraken, comptes_bancaires
                FROM portfolios WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'pea': json.loads(result[0] or '[]'),
                    'compte_titre': json.loads(result[1] or '[]'),
                    'crypto_kraken': json.loads(result[2] or '[]'),
                    'comptes_bancaires': json.loads(result[3] or '[]')
                }
    except Exception as e:
        print(f"Erreur récupération portefeuille: {e}")
    
    return {
        'pea': [],
        'compte_titre': [],
        'crypto_kraken': [],
        'comptes_bancaires': []
    }

def save_user_portfolio(user_id: int, portfolio: Dict) -> bool:
    """Sauvegarde le portefeuille d'un utilisateur"""
    try:
        # S'assurer que toutes les clés sont présentes avec des valeurs par défaut
        # Le portfolio passé devrait toujours contenir toutes les données du session_state
        merged_portfolio = {
            'pea': portfolio.get('pea', []),
            'compte_titre': portfolio.get('compte_titre', []),
            'crypto_kraken': portfolio.get('crypto_kraken', []),
            'comptes_bancaires': portfolio.get('comptes_bancaires', [])
        }
        
        if is_using_supabase():
            client = get_supabase_client()
            
            portfolio_data = {
                'pea': json.dumps(merged_portfolio.get('pea', [])),
                'compte_titre': json.dumps(merged_portfolio.get('compte_titre', [])),
                'crypto_kraken': json.dumps(merged_portfolio.get('crypto_kraken', [])),
                'comptes_bancaires': json.dumps(merged_portfolio.get('comptes_bancaires', [])),
                'updated_at': datetime.now().isoformat()
            }
            
            # Vérifier si le portefeuille existe
            existing = client.table('portfolios').select('id').eq('user_id', user_id).execute()
            
            if existing.data:
                # Mise à jour
                result = client.table('portfolios').update(portfolio_data).eq('user_id', user_id).execute()
                if hasattr(result, 'data') and result.data:
                    return True
                else:
                    print(f"❌ Erreur Supabase UPDATE: {result}")
                    return False
            else:
                # Création
                portfolio_data['user_id'] = user_id
                result = client.table('portfolios').insert(portfolio_data).execute()
                if hasattr(result, 'data') and result.data:
                    return True
                else:
                    print(f"❌ Erreur Supabase INSERT: {result}")
                    return False
        else:
            # Fallback SQLite
            conn = get_sqlite_connection()
            cursor = conn.cursor()
            
            # Vérifier si existe
            cursor.execute('SELECT id FROM portfolios WHERE user_id = ?', (user_id,))
            portfolio_exists = cursor.fetchone()
            
            if portfolio_exists:
                cursor.execute('''
                    UPDATE portfolios
                    SET pea = ?, compte_titre = ?, crypto_kraken = ?, comptes_bancaires = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (
                    json.dumps(merged_portfolio.get('pea', [])),
                    json.dumps(merged_portfolio.get('compte_titre', [])),
                    json.dumps(merged_portfolio.get('crypto_kraken', [])),
                    json.dumps(merged_portfolio.get('comptes_bancaires', [])),
                    user_id
                ))
            else:
                cursor.execute('''
                    INSERT INTO portfolios (user_id, pea, compte_titre, crypto_kraken, comptes_bancaires)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    json.dumps(merged_portfolio.get('pea', [])),
                    json.dumps(merged_portfolio.get('compte_titre', [])),
                    json.dumps(merged_portfolio.get('crypto_kraken', [])),
                    json.dumps(merged_portfolio.get('comptes_bancaires', []))
                ))
            
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        print(f"❌ Erreur sauvegarde portefeuille: {e}")
        import traceback
        traceback.print_exc()
        return False

def save_analysis(user_id: int, analysis_data: List[Dict], scan_date: str) -> bool:
    """Sauvegarde une analyse pour un utilisateur"""
    try:
        if is_using_supabase():
            client = get_supabase_client()
            client.table('saved_analyses').insert({
                'user_id': user_id,
                'analysis_data': json.dumps(analysis_data),
                'scan_date': scan_date
            }).execute()
            return True
        else:
            conn = get_sqlite_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO saved_analyses (user_id, analysis_data, scan_date)
                VALUES (?, ?, ?)
            ''', (user_id, json.dumps(analysis_data), scan_date))
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        print(f"Erreur sauvegarde analyse: {e}")
        return False

def get_user_analyses(user_id: int, limit: int = 10) -> List[Dict]:
    """Récupère les analyses sauvegardées d'un utilisateur"""
    try:
        if is_using_supabase():
            client = get_supabase_client()
            result = client.table('saved_analyses').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
            
            analyses = []
            for row in result.data:
                analyses.append({
                    'data': json.loads(row['analysis_data']),
                    'scan_date': row['scan_date'],
                    'created_at': row['created_at']
                })
            return analyses
        else:
            conn = get_sqlite_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT analysis_data, scan_date, created_at
                FROM saved_analyses
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            analyses = []
            for result in results:
                analyses.append({
                    'data': json.loads(result[0]),
                    'scan_date': result[1],
                    'created_at': result[2]
                })
            return analyses
    except Exception as e:
        print(f"Erreur récupération analyses: {e}")
        return []

def check_rate_limit(user_id: Optional[int], ip_address: str, action: str, max_requests: int = 10, window_minutes: int = 1) -> bool:
    """Vérifie si l'utilisateur/IP a dépassé la limite de requêtes"""
    try:
        window_start = (datetime.now() - timedelta(minutes=window_minutes)).isoformat()
        
        if is_using_supabase():
            client = get_supabase_client()
            
            # Nettoyer les anciennes entrées
            client.table('rate_limiting').delete().lt('timestamp', window_start).execute()
            
            # Compter les requêtes
            if user_id:
                result = client.table('rate_limiting').select('id', count='exact').eq('user_id', user_id).eq('action', action).gt('timestamp', window_start).execute()
            else:
                result = client.table('rate_limiting').select('id', count='exact').eq('ip_address', ip_address).eq('action', action).gt('timestamp', window_start).execute()
            
            count = result.count if hasattr(result, 'count') else len(result.data)
            
            if count >= max_requests:
                return True
            
            # Enregistrer cette requête
            client.table('rate_limiting').insert({
                'user_id': user_id,
                'ip_address': ip_address,
                'action': action
            }).execute()
            
            return False
        else:
            # Fallback SQLite
            conn = get_sqlite_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM rate_limiting WHERE timestamp < datetime('now', '-1 hour')")
            window_start_str = window_start
            
            if user_id:
                cursor.execute('''
                    SELECT COUNT(*) FROM rate_limiting
                    WHERE user_id = ? AND action = ? AND timestamp > ?
                ''', (user_id, action, window_start_str))
            else:
                cursor.execute('''
                    SELECT COUNT(*) FROM rate_limiting
                    WHERE ip_address = ? AND action = ? AND timestamp > ?
                ''', (ip_address, action, window_start_str))
            
            count = cursor.fetchone()[0]
            
            if count >= max_requests:
                conn.close()
                return True
            
            cursor.execute('''
                INSERT INTO rate_limiting (user_id, ip_address, action)
                VALUES (?, ?, ?)
            ''', (user_id, ip_address, action))
            
            conn.commit()
            conn.close()
            return False
    except Exception as e:
        print(f"Erreur rate limiting: {e}")
        return False

def get_database_info() -> Dict[str, str]:
    """Retourne des informations sur la base de données utilisée"""
    info = {
        'type': 'Inconnu',
        'status': 'Non connecté',
        'host': 'N/A',
        'database': 'N/A',
        'error': None
    }
    
    if not SUPABASE_AVAILABLE:
        info['type'] = 'SQLite (Local)'
        info['status'] = '⚠️ supabase-py non installé - Mode local'
        info['error'] = 'supabase>=2.0.0 manquant dans requirements.txt'
        return info
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        info['type'] = 'SQLite (Local)'
        info['status'] = '⚠️ SUPABASE_URL ou SUPABASE_KEY non défini - Mode local'
        info['error'] = 'SUPABASE_URL et SUPABASE_KEY manquants dans les secrets Streamlit'
        return info
    
    try:
        if is_using_supabase():
            info['type'] = 'Supabase (API)'
            info['status'] = '✅ Connecté'
            info['host'] = SUPABASE_URL
            info['database'] = 'Supabase Cloud'
        else:
            info['type'] = 'SQLite (Local)'
            info['status'] = '⚠️ Mode local (connexion Supabase échouée)'
            info['error'] = 'Connexion Supabase échouée - vérifiez SUPABASE_URL et SUPABASE_KEY'
    except Exception as e:
        error_msg = str(e)
        info['type'] = 'SQLite (Local)'
        info['status'] = f'❌ Erreur connexion: {error_msg[:50]}'
        info['error'] = error_msg
    
    return info

# Initialiser la base de données
init_database()

