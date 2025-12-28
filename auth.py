"""
Module d'authentification pour l'application Agent Bourse
Gère la connexion, l'inscription et la session utilisateur
Sécurité améliorée avec validation et rate limiting
"""
import streamlit as st
from database import (
    create_user, verify_user, user_exists, email_exists,
    get_user_portfolio, save_user_portfolio, check_rate_limit, is_valid_email
)

def init_session_state():
    """Initialise les variables de session"""
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None
    if 'username' not in st.session_state:
        st.session_state['username'] = None

def get_client_ip():
    """Récupère l'adresse IP du client (approximation pour Streamlit)"""
    try:
        # Streamlit ne donne pas directement l'IP, on utilise une approximation
        # En production, on pourrait utiliser st.session_state avec un identifiant unique
        return st.session_state.get('client_id', 'unknown')
    except:
        return 'unknown'

def show_login_form():
    """Affiche le formulaire de connexion avec protection rate limiting"""
    st.markdown("### 🔐 Connexion")
    
    # Initialiser client_id si nécessaire
    if 'client_id' not in st.session_state:
        import uuid
        st.session_state['client_id'] = str(uuid.uuid4())
    
    ip_address = get_client_ip()
    
    # Vérifier le rate limiting
    if check_rate_limit(None, ip_address, 'login', max_requests=5, window_minutes=5):
        st.error("⚠️ Trop de tentatives de connexion. Veuillez attendre quelques minutes.")
        return
    
    with st.form("login_form"):
        username = st.text_input("Nom d'utilisateur", key="login_username")
        password = st.text_input("Mot de passe", type="password", key="login_password")
        submit = st.form_submit_button("Se connecter", use_container_width=True)
        
        if submit:
            if username and password:
                try:
                    user_id = verify_user(username, password, ip_address)
                    if user_id:
                        st.session_state['authenticated'] = True
                        st.session_state['user_id'] = user_id
                        st.session_state['username'] = username
                        st.success(f"✅ Bienvenue {username} !")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ {str(e)}")
            else:
                st.warning("⚠️ Veuillez remplir tous les champs")

def show_register_form():
    """Affiche le formulaire d'inscription avec validation améliorée"""
    st.markdown("### 📝 Inscription")
    
    # Initialiser client_id si nécessaire
    if 'client_id' not in st.session_state:
        import uuid
        st.session_state['client_id'] = str(uuid.uuid4())
    
    ip_address = get_client_ip()
    
    # Vérifier le rate limiting
    if check_rate_limit(None, ip_address, 'register', max_requests=3, window_minutes=10):
        st.error("⚠️ Trop de tentatives d'inscription. Veuillez attendre quelques minutes.")
        return
    
    with st.form("register_form"):
        username = st.text_input("Nom d'utilisateur (3-20 caractères, lettres, chiffres, _)", key="reg_username")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Mot de passe (minimum 6 caractères)", type="password", key="reg_password")
        password_confirm = st.text_input("Confirmer le mot de passe", type="password", key="reg_password_confirm")
        submit = st.form_submit_button("S'inscrire", use_container_width=True)
        
        if submit:
            if not username or not email or not password:
                st.warning("⚠️ Veuillez remplir tous les champs")
            elif password != password_confirm:
                st.error("❌ Les mots de passe ne correspondent pas")
            elif len(password) < 6:
                st.error("❌ Le mot de passe doit contenir au moins 6 caractères")
            elif not is_valid_email(email):
                st.error("❌ Format d'email invalide")
            elif user_exists(username):
                st.error("❌ Ce nom d'utilisateur est déjà pris")
            elif email_exists(email):
                st.error("❌ Cet email est déjà utilisé")
            else:
                user_id = create_user(username, email, password)
                if user_id:
                    st.success("✅ Inscription réussie ! Vous pouvez maintenant vous connecter.")
                else:
                    st.error("❌ Erreur lors de l'inscription. Vérifiez que le nom d'utilisateur et l'email sont valides.")

def show_auth_page():
    """Affiche la page d'authentification"""
    st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='font-size: 2.5rem; margin-bottom: 1rem;'>📊 Agent Bourse</h1>
            <p style='color: #64748b; font-size: 1.1rem;'>Connectez-vous pour accéder à votre portefeuille</p>
        </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Connexion", "📝 Inscription"])
    
    with tab1:
        show_login_form()
    
    with tab2:
        show_register_form()

def logout():
    """Déconnecte l'utilisateur"""
    st.session_state['authenticated'] = False
    st.session_state['user_id'] = None
    st.session_state['username'] = None
    if 'portfolio' in st.session_state:
        del st.session_state['portfolio']
    st.rerun()

def require_auth():
    """Vérifie si l'utilisateur est authentifié, sinon affiche la page de connexion"""
    init_session_state()
    
    if not st.session_state['authenticated']:
        show_auth_page()
        st.stop()
    
    # Charger le portefeuille de l'utilisateur
    if 'portfolio' not in st.session_state or st.session_state.get('portfolio_loaded') != st.session_state['user_id']:
        st.session_state['portfolio'] = get_user_portfolio(st.session_state['user_id'])
        st.session_state['portfolio_loaded'] = st.session_state['user_id']

def save_portfolio_to_db(portfolio: dict) -> bool:
    """Sauvegarde le portefeuille dans la base de données"""
    if st.session_state.get('authenticated') and st.session_state.get('user_id'):
        return save_user_portfolio(st.session_state['user_id'], portfolio)
    return False

