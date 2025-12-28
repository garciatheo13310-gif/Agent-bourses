"""
Module de gestion de la base de données pour l'application Agent Bourse
Utilise SQLite pour le stockage des utilisateurs et portefeuilles
"""
import sqlite3
import json
import hashlib
import os
from datetime import datetime
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
            last_login TIMESTAMP
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
            scan_date TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """Hash un mot de passe avec SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username: str, email: str, password: str) -> Optional[int]:
    """Crée un nouvel utilisateur"""
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

def verify_user(username: str, password: str) -> Optional[int]:
    """Vérifie les identifiants et retourne l'ID utilisateur si valide"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    password_hash = hash_password(password)
    cursor.execute('''
        SELECT id FROM users
        WHERE username = ? AND password_hash = ?
    ''', (username, password_hash))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        # Mettre à jour la date de dernière connexion
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET last_login = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (result[0],))
        conn.commit()
        conn.close()
        return result[0]
    return None

def get_user_portfolio(user_id: int) -> Dict:
    """Récupère le portefeuille d'un utilisateur"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT pea, compte_titre, crypto_kraken, comptes_bancaires
        FROM portfolios
        WHERE user_id = ?
    ''', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'pea': json.loads(result[0]) if result[0] else [],
            'compte_titre': json.loads(result[1]) if result[1] else [],
            'crypto_kraken': json.loads(result[2]) if result[2] else [],
            'comptes_bancaires': json.loads(result[3]) if result[3] else []
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, analysis_data, scan_date, created_at
        FROM saved_analyses
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    
    results = cursor.fetchall()
    conn.close()
    
    analyses = []
    for row in results:
        analyses.append({
            'id': row[0],
            'data': json.loads(row[1]),
            'scan_date': row[2],
            'created_at': row[3]
        })
    
    return analyses

def user_exists(username: str) -> bool:
    """Vérifie si un utilisateur existe"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

# Initialiser la base de données au chargement du module
init_database()

