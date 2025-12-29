"""
Module de gestion de la base de données pour l'application Agent Bourse
Version PostgreSQL pour persistance réelle sur Streamlit Cloud
"""
import json
import bcrypt
import re
import os
from urllib.parse import quote_plus, urlparse, urlunparse
from datetime import datetime, timedelta
from typing import Optional, Dict, List

# Essayer d'importer psycopg2 (PostgreSQL), sinon utiliser SQLite
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    print("⚠️ psycopg2 non disponible, utilisation de SQLite")

# Récupérer l'URL de connexion PostgreSQL depuis les variables d'environnement
DATABASE_URL = os.getenv('DATABASE_URL')

# Variable globale pour tracker le type de DB réellement utilisé
_using_postgresql = None

def is_using_postgresql(conn=None):
    """Détecte si on utilise PostgreSQL ou SQLite"""
    global _using_postgresql
    if _using_postgresql is not None:
        return _using_postgresql
    
    if conn:
        # Vérifier le type de connexion
        _using_postgresql = hasattr(conn, 'server_version') or type(conn).__module__ == 'psycopg2'
        return _using_postgresql
    
    # Tester la connexion
    try:
        test_conn = get_connection()
        _using_postgresql = hasattr(test_conn, 'server_version') or type(test_conn).__module__ == 'psycopg2'
        test_conn.close()
        return _using_postgresql
    except:
        _using_postgresql = False
        return False

def get_connection():
    """Obtient une connexion à la base de données (PostgreSQL ou SQLite)"""
    global _using_postgresql
    if POSTGRESQL_AVAILABLE and DATABASE_URL:
        # Utiliser PostgreSQL
        try:
            # Encoder l'URL pour gérer les caractères spéciaux dans le mot de passe
            from urllib.parse import quote_plus, urlparse, urlunparse
            parsed = urlparse(DATABASE_URL)
            # Encoder le mot de passe si nécessaire
            if parsed.password:
                # Reconstruire l'URL avec le mot de passe encodé
                encoded_password = quote_plus(parsed.password)
                encoded_url = urlunparse((
                    parsed.scheme,
                    f"{parsed.username}:{encoded_password}@{parsed.hostname}:{parsed.port or 5432}",
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
                conn = psycopg2.connect(encoded_url, connect_timeout=10)
                _using_postgresql = True
                return conn
            else:
                conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
                _using_postgresql = True
                return conn
        except Exception as e:
            print(f"⚠️ Erreur connexion PostgreSQL: {str(e)[:100]}")
            # Fallback vers SQLite en cas d'erreur
            print("⚠️ Fallback vers SQLite...")
            _using_postgresql = False
            import sqlite3
            DB_PATH = os.path.join(os.path.dirname(__file__), 'agent_bourse.db')
            return sqlite3.connect(DB_PATH)
    else:
        # Fallback vers SQLite
        _using_postgresql = False
        import sqlite3
        DB_PATH = os.path.join(os.path.dirname(__file__), 'agent_bourse.db')
        return sqlite3.connect(DB_PATH)

def init_database():
    """Initialise la base de données avec les tables nécessaires"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Détecter le type de DB réellement utilisé
    is_pg = is_using_postgresql(conn)
    
    if is_pg:
        # PostgreSQL
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
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
            CREATE TABLE IF NOT EXISTS rate_limiting (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                ip_address VARCHAR(45),
                action VARCHAR(50) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolios (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                pea TEXT DEFAULT '[]',
                compte_titre TEXT DEFAULT '[]',
                crypto_kraken TEXT DEFAULT '[]',
                comptes_bancaires TEXT DEFAULT '[]',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_analyses (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                analysis_data TEXT NOT NULL,
                scan_date VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Index pour améliorer les performances
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rate_limiting_user ON rate_limiting(user_id, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rate_limiting_ip ON rate_limiting(ip_address, timestamp)')
    else:
        # SQLite (fallback)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rate_limiting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ip_address TEXT,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                pea TEXT DEFAULT '[]',
                compte_titre TEXT DEFAULT '[]',
                crypto_kraken TEXT DEFAULT '[]',
                comptes_bancaires TEXT DEFAULT '[]',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                analysis_data TEXT NOT NULL,
                scan_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rate_limiting_user ON rate_limiting(user_id, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rate_limiting_ip ON rate_limiting(ip_address, timestamp)')
    
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Vérifie un mot de passe contre son hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except:
        try:
            import hashlib
            sha256_hash = hashlib.sha256(password.encode()).hexdigest()
            return sha256_hash == password_hash
        except:
            return False

def is_valid_email(email: str) -> bool:
    """Valide le format d'un email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def check_rate_limit(user_id: Optional[int], ip_address: str, action: str, max_requests: int = 10, window_minutes: int = 1) -> bool:
    """Vérifie si l'utilisateur/IP a dépassé la limite de requêtes"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Détecter le type de DB réellement utilisé
        is_pg = is_using_postgresql(conn)
        
        # Nettoyer les anciennes entrées
        if is_pg:
            cursor.execute("DELETE FROM rate_limiting WHERE timestamp < NOW() - INTERVAL '1 hour'")
            window_start = datetime.now() - timedelta(minutes=window_minutes)
        else:
            cursor.execute("DELETE FROM rate_limiting WHERE timestamp < datetime('now', '-1 hour')")
            window_start = (datetime.now() - timedelta(minutes=window_minutes)).isoformat()
        
        # Compter les requêtes
        if user_id:
            if is_pg:
                cursor.execute('''
                    SELECT COUNT(*) FROM rate_limiting
                    WHERE user_id = %s AND action = %s AND timestamp > %s
                ''', (user_id, action, window_start))
            else:
                cursor.execute('''
                    SELECT COUNT(*) FROM rate_limiting
                    WHERE user_id = ? AND action = ? AND timestamp > ?
                ''', (user_id, action, window_start))
        else:
            if is_pg:
                cursor.execute('''
                    SELECT COUNT(*) FROM rate_limiting
                    WHERE ip_address = %s AND action = %s AND timestamp > %s
                ''', (ip_address, action, window_start))
            else:
                cursor.execute('''
                    SELECT COUNT(*) FROM rate_limiting
                    WHERE ip_address = ? AND action = ? AND timestamp > ?
                ''', (ip_address, action, window_start))
        
        count = cursor.fetchone()[0]
        
        if count >= max_requests:
            conn.close()
            return True
        
        # Enregistrer cette requête
        if is_pg:
            cursor.execute('''
                INSERT INTO rate_limiting (user_id, ip_address, action)
                VALUES (%s, %s, %s)
            ''', (user_id, ip_address, action))
        else:
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

def create_user(username: str, email: str, password: str) -> Optional[int]:
    """Crée un nouvel utilisateur avec validation"""
    if not is_valid_email(email):
        return None
    
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return None
    
    if len(password) < 6:
        return None
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Détecter le type de DB réellement utilisé
        is_pg = is_using_postgresql(conn)
        
        password_hash = hash_password(password)
        
        if is_pg:
            cursor.execute('''
                INSERT INTO users (username, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id
            ''', (username, email, password_hash))
            user_id = cursor.fetchone()[0]
        else:
            cursor.execute('''
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
            ''', (username, email, password_hash))
            user_id = cursor.lastrowid
        
        # Créer un portefeuille vide
        if is_pg:
            cursor.execute('''
                INSERT INTO portfolios (user_id, pea, compte_titre, crypto_kraken, comptes_bancaires)
                VALUES (%s, %s, %s, %s, %s)
            ''', (user_id, '[]', '[]', '[]', '[]'))
        else:
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
    """Vérifie les identifiants avec protection contre les attaques"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Détecter le type de DB réellement utilisé
    is_pg = is_using_postgresql(conn)
    
    if is_pg:
        cursor.execute('''
            SELECT id, password_hash, failed_login_attempts, locked_until
            FROM users WHERE username = %s
        ''', (username,))
    else:
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
            if isinstance(locked_until, str):
                locked_until_dt = datetime.fromisoformat(locked_until)
            else:
                locked_until_dt = locked_until
            if datetime.now() < locked_until_dt:
                remaining = (locked_until_dt - datetime.now()).seconds // 60
                conn.close()
                raise Exception(f"Compte bloqué. Réessayez dans {remaining} minutes.")
        except:
            pass
    
    # Vérifier le mot de passe
    if verify_password(password, stored_hash):
        # Connexion réussie
        if is_pg:
            cursor.execute('''
                UPDATE users 
                SET last_login = CURRENT_TIMESTAMP,
                    failed_login_attempts = 0,
                    locked_until = NULL
                WHERE id = %s
            ''', (user_id,))
        else:
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
        # Échec - incrémenter tentatives
        failed_attempts = (failed_attempts or 0) + 1
        
        if failed_attempts >= 5:
            locked_until = (datetime.now() + timedelta(minutes=30)).isoformat()
            if is_pg:
                cursor.execute('''
                    UPDATE users 
                    SET failed_login_attempts = %s, locked_until = %s
                    WHERE id = %s
                ''', (failed_attempts, locked_until, user_id))
            else:
                cursor.execute('''
                    UPDATE users 
                    SET failed_login_attempts = ?, locked_until = ?
                    WHERE id = ?
                ''', (failed_attempts, locked_until, user_id))
        else:
            if is_pg:
                cursor.execute('''
                    UPDATE users SET failed_login_attempts = %s WHERE id = %s
                ''', (failed_attempts, user_id))
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

def user_exists(username: str) -> bool:
    """Vérifie si un utilisateur existe"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Détecter le type de DB réellement utilisé
    is_pg = is_using_postgresql(conn)
    
    if is_pg:
        cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
    else:
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    
    result = cursor.fetchone()
    conn.close()
    return result is not None

def email_exists(email: str) -> bool:
    """Vérifie si un email existe"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Détecter le type de DB réellement utilisé
    is_pg = is_using_postgresql(conn)
    
    if is_pg:
        cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
    else:
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_user_email(user_id: int) -> Optional[str]:
    """Récupère l'email d'un utilisateur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Détecter le type de DB réellement utilisé
    is_pg = is_using_postgresql(conn)
    
    if is_pg:
        cursor.execute('SELECT email FROM users WHERE id = %s', (user_id,))
    else:
        cursor.execute('SELECT email FROM users WHERE id = ?', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def get_user_portfolio(user_id: int) -> Dict:
    """Récupère le portefeuille d'un utilisateur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Détecter le type de DB réellement utilisé
    is_pg = is_using_postgresql(conn)
    
    if is_pg:
        cursor.execute('''
            SELECT pea, compte_titre, crypto_kraken, comptes_bancaires
            FROM portfolios WHERE user_id = %s
        ''', (user_id,))
    else:
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
    
    return {
        'pea': [],
        'compte_titre': [],
        'crypto_kraken': [],
        'comptes_bancaires': []
    }

def save_user_portfolio(user_id: int, portfolio: Dict) -> bool:
    """Sauvegarde le portefeuille d'un utilisateur"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Détecter le type de DB réellement utilisé
        is_pg = is_using_postgresql(conn)
        
        if is_pg:
            cursor.execute('''
                UPDATE portfolios
                SET pea = %s, compte_titre = %s, crypto_kraken = %s, comptes_bancaires = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            ''', (
                json.dumps(portfolio.get('pea', [])),
                json.dumps(portfolio.get('compte_titre', [])),
                json.dumps(portfolio.get('crypto_kraken', [])),
                json.dumps(portfolio.get('comptes_bancaires', [])),
                user_id
            ))
        else:
            cursor.execute('''
                UPDATE portfolios
                SET pea = ?, compte_titre = ?, crypto_kraken = ?, comptes_bancaires = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (
                json.dumps(portfolio.get('pea', [])),
                json.dumps(portfolio.get('compte_titre', [])),
                json.dumps(portfolio.get('crypto_kraken', [])),
                json.dumps(portfolio.get('comptes_bancaires', [])),
                user_id
            ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erreur sauvegarde portefeuille: {e}")
        return False

def save_analysis(user_id: int, analysis_data: List[Dict], scan_date: str) -> bool:
    """Sauvegarde une analyse pour un utilisateur"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Détecter le type de DB réellement utilisé
        is_pg = is_using_postgresql(conn)
        
        if is_pg:
            cursor.execute('''
                INSERT INTO saved_analyses (user_id, analysis_data, scan_date)
                VALUES (%s, %s, %s)
            ''', (user_id, json.dumps(analysis_data), scan_date))
        else:
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
        conn = get_connection()
        cursor = conn.cursor()
        
        # Détecter le type de DB réellement utilisé
        is_pg = is_using_postgresql(conn)
        
        if is_pg:
            cursor.execute('''
                SELECT analysis_data, scan_date, created_at
                FROM saved_analyses
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            ''', (user_id, limit))
        else:
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

# Initialiser la base de données
init_database()

