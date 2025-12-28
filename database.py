"""
Module de gestion de la base de données pour l'application Agent Bourse
Utilise SQLite pour le stockage des utilisateurs et portefeuilles
Sécurité améliorée avec bcrypt et rate limiting
"""
import sqlite3
import json
import hashlib
import os
import bcrypt
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List

DB_PATH = os.path.join(os.path.dirname(__file__), 'agent_bourse.db')

def init_database():
    """Initialise la base de données avec les tables nécessaires"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table des utilisateurs
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
    
    # Table pour le rate limiting
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
    
    # Table des portefeuilles
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
    
    # Table des analyses sauvegardées
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
    
    # Index pour améliorer les performances
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rate_limiting_user ON rate_limiting(user_id, timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rate_limiting_ip ON rate_limiting(ip_address, timestamp)')
    
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt (plus sûr que SHA256)"""
    # Générer un salt et hasher le mot de passe
    salt = bcrypt.gensalt(rounds=12)  # 12 rounds = bon équilibre sécurité/performance
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Vérifie un mot de passe contre son hash"""
    try:
        # Essayer bcrypt d'abord
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except:
        # Fallback pour les anciens mots de passe SHA256 (migration)
        try:
            sha256_hash = hashlib.sha256(password.encode()).hexdigest()
            return sha256_hash == password_hash
        except:
            return False

def is_valid_email(email: str) -> bool:
    """Valide le format d'un email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def check_rate_limit(user_id: Optional[int], ip_address: str, action: str, max_requests: int = 10, window_minutes: int = 1) -> bool:
    """Vérifie si l'utilisateur/IP a dépassé la limite de requêtes
    Retourne True si la limite est dépassée (bloqué)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Nettoyer les anciennes entrées (plus de 1 heure)
        cursor.execute('''
            DELETE FROM rate_limiting 
            WHERE timestamp < datetime('now', '-1 hour')
        ''')
        
        # Compter les requêtes dans la fenêtre de temps
        window_start = (datetime.now() - timedelta(minutes=window_minutes)).isoformat()
        
        if user_id:
            cursor.execute('''
                SELECT COUNT(*) FROM rate_limiting
                WHERE user_id = ? AND action = ? AND timestamp > ?
            ''', (user_id, action, window_start))
        else:
            cursor.execute('''
                SELECT COUNT(*) FROM rate_limiting
                WHERE ip_address = ? AND action = ? AND timestamp > ?
            ''', (ip_address, action, window_start))
        
        count = cursor.fetchone()[0]
        
        if count >= max_requests:
            conn.close()
            return True  # Limite dépassée
        
        # Enregistrer cette requête
        cursor.execute('''
            INSERT INTO rate_limiting (user_id, ip_address, action)
            VALUES (?, ?, ?)
        ''', (user_id, ip_address, action))
        
        conn.commit()
        conn.close()
        return False  # OK
    except Exception as e:
        print(f"Erreur rate limiting: {e}")
        return False  # En cas d'erreur, on laisse passer

def create_user(username: str, email: str, password: str) -> Optional[int]:
    """Crée un nouvel utilisateur avec validation"""
    # Validation de l'email
    if not is_valid_email(email):
        return None
    
    # Validation du nom d'utilisateur (alphanumérique + underscore, 3-20 caractères)
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return None
    
    # Validation du mot de passe (minimum 6 caractères)
    if len(password) < 6:
        return None
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        cursor.execute('''
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        ''', (username, email, password_hash))
        
        user_id = cursor.lastrowid
        
        # Créer un portefeuille vide pour l'utilisateur
        cursor.execute('''
            INSERT INTO portfolios (user_id, pea, compte_titre, crypto_kraken, comptes_bancaires)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, '[]', '[]', '[]', '[]'))
        
        conn.commit()
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        return None

def verify_user(username: str, password: str, ip_address: str = None) -> Optional[int]:
    """Vérifie les identifiants et retourne l'ID utilisateur si valide
    Gère aussi le blocage après trop de tentatives"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Vérifier si le compte est bloqué
    cursor.execute('''
        SELECT id, password_hash, failed_login_attempts, locked_until
        FROM users WHERE username = ?
    ''', (username,))
    
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return None
    
    user_id, stored_hash, failed_attempts, locked_until = result
    
    # Vérifier si le compte est bloqué
    if locked_until:
        try:
            locked_until_dt = datetime.fromisoformat(locked_until)
            if datetime.now() < locked_until_dt:
                remaining = (locked_until_dt - datetime.now()).seconds // 60
                conn.close()
                raise Exception(f"Compte bloqué. Réessayez dans {remaining} minutes.")
        except:
            pass  # Si erreur de parsing, on continue
    
    # Vérifier le mot de passe
    if verify_password(password, stored_hash):
        # Connexion réussie - réinitialiser les tentatives
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
        # Échec de connexion - incrémenter les tentatives
        failed_attempts = (failed_attempts or 0) + 1
        
        # Bloquer après 5 tentatives échouées (pendant 30 minutes)
        if failed_attempts >= 5:
            locked_until = (datetime.now() + timedelta(minutes=30)).isoformat()
            cursor.execute('''
                UPDATE users 
                SET failed_login_attempts = ?,
                    locked_until = ?
                WHERE id = ?
            ''', (failed_attempts, locked_until, user_id))
        else:
            cursor.execute('''
                UPDATE users 
                SET failed_login_attempts = ?
                WHERE id = ?
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def email_exists(email: str) -> bool:
    """Vérifie si un email existe"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_user_portfolio(user_id: int) -> Dict:
    """Récupère le portefeuille d'un utilisateur"""
    conn = sqlite3.connect(DB_PATH)
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
    
    # Si pas de portefeuille, retourner un portefeuille vide
    return {
        'pea': [],
        'compte_titre': [],
        'crypto_kraken': [],
        'comptes_bancaires': []
    }

def save_user_portfolio(user_id: int, portfolio: Dict) -> bool:
    """Sauvegarde le portefeuille d'un utilisateur"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
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
        conn = sqlite3.connect(DB_PATH)
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
        conn = sqlite3.connect(DB_PATH)
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

# Initialiser la base de données au chargement du module
init_database()
