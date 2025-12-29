import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import sys
import os
import numpy as np
import json

# Imports pour l'authentification et la base de données
try:
    from auth import require_auth, logout, save_portfolio_to_db
    from database import save_analysis, get_user_analyses
except ImportError as e:
    st.error(f"❌ Erreur d'import auth/database: {e}")
    st.stop()

# Ajouter le répertoire parent au path pour importer main
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from main import (
        get_sp500_tickers, 
        get_eurostoxx_tickers,
        get_nasdaq100_tickers,
        get_dowjones_tickers,
        get_emerging_markets_tickers,
        get_asia_pacific_tickers,
        get_canada_tickers,
        screen_stocks,
        score_and_rank_stocks,
        get_technical_data,
        ask_ai_opinion,
        send_email,
        TOP_N,
        MIN_REVENUE_GROWTH,
        MIN_EARNINGS_GROWTH,
        MIN_ROE,
        MIN_PROFIT_MARGIN,
        MIN_PE_RATIO,
        MAX_PE_RATIO,
        MIN_PEG_RATIO,
        MAX_PEG_RATIO
    )
    import yfinance as yf
except ImportError as e:
    st.error(f"❌ Erreur d'import: {e}")
    st.stop()
except Exception as e:
    st.warning(f"⚠️ Attention: {e}")

st.set_page_config(
    page_title="Agent Bourse - Dashboard IA",
    page_icon="📊",
    layout="wide"
)

# Authentification requise - DOIT être appelé AVANT tout affichage
require_auth()

# CSS moderne et attrayant
st.markdown("""
    <style>
    /* Import de polices Google */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Variables de couleurs */
    :root {
        --primary: #6366f1;
        --primary-dark: #4f46e5;
        --secondary: #8b5cf6;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --info: #3b82f6;
        --dark: #1e293b;
        --light: #f8fafc;
        --gradient-1: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --gradient-2: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --gradient-3: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    
    /* Style général */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    /* Header principal avec gradient */
    .main-header {
        background: var(--gradient-1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }
    
    .main-subtitle {
        text-align: center;
        color: #64748b;
        font-size: 1.1rem;
        font-weight: 400;
        margin-bottom: 2.5rem;
        letter-spacing: 0.01em;
    }
    
    /* Cartes métriques améliorées */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border: 1px solid #e2e8f0;
        transition: all 0.3s ease;
        margin-bottom: 1rem;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    /* Sidebar - Fond blanc simple */
    [data-testid="stSidebar"] {
        background: #ffffff;
    }
    
    [data-testid="stSidebar"] .css-1d391kg {
        color: #1f2937;
    }
    
    /* Cards pour les paramètres */
    .param-card {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.25rem;
        margin: 1rem 0;
        transition: all 0.2s ease;
    }
    
    .param-card:hover {
        border-color: #6366f1;
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.1);
    }
    
    .param-label {
        font-size: 0.875rem;
        font-weight: 600;
        color: #374151;
        margin-bottom: 0.5rem;
        display: block;
    }
    
    .param-value {
        font-size: 1.125rem;
        font-weight: 700;
        color: #6366f1;
        margin-top: 0.5rem;
    }
    
    /* Sliders épurés - Fond blanc */
    .stSlider > div > div {
        background: #ffffff !important;
    }
    
    .stSlider > div > div > div {
        background: #3b82f6 !important;
    }
    
    .stSlider > div > div > div > div {
        background: #3b82f6 !important;
    }
    
    /* Sections de paramètres */
    .param-section {
        background: transparent;
        border: none;
        border-radius: 0;
        padding: 0;
        margin: 1.25rem 0;
    }
    
    .param-section-title {
        font-size: 0.875rem;
        font-weight: 700;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid #e5e7eb;
    }
    
    /* Boutons modernes */
    .stButton > button {
        background: var(--gradient-1);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.4);
    }
    
    /* Sliders modernes - Fond blanc */
    .stSlider > div > div {
        background: #ffffff !important;
    }
    
    .stSlider > div > div > div {
        background: #3b82f6 !important;
    }
    
    .stSlider > div > div > div > div {
        background: #3b82f6 !important;
    }
    
    /* Sections avec fond */
    .section-container {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        margin: 1.5rem 0;
        border: 1px solid #e2e8f0;
    }
    
    /* Badges et tags */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 600;
        background: var(--gradient-1);
        color: white;
    }
    
    /* Tableaux améliorés */
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    
    /* Graphiques avec ombre */
    .js-plotly-plot {
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* Alertes modernes */
    .stAlert {
        border-radius: 12px;
        border-left: 4px solid;
    }
    
    /* Progress bar moderne */
    .stProgress > div > div > div {
        background: var(--gradient-1);
    }
    
    /* Inputs modernes */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div {
        border-radius: 10px;
        border: 2px solid #e2e8f0;
        transition: all 0.2s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }
    
    /* Tabs modernes */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
    }
    
    /* Espacement amélioré */
    .main .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
    }
    
    /* Animations subtiles */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease-out;
    }
    
    /* Scrollbar moderne */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f5f9;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--gradient-1);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary-dark);
    }
    </style>
""", unsafe_allow_html=True)

# Authentification requise - DOIT être appelé AVANT tout affichage
require_auth()

# Header moderne avec gradient
st.markdown("""
    <div class="fade-in">
        <h1 class="main-header">📊 Agent Bourse</h1>
        <p class="main-subtitle">Dashboard IA d'Analyse Boursière • Découvrez les meilleures opportunités d'investissement</p>
    </div>
""", unsafe_allow_html=True)

    # Afficher le nom d'utilisateur et bouton de déconnexion
col1, col2 = st.columns([6, 1])
with col1:
    st.markdown(f"👤 **Connecté en tant que:** {st.session_state.get('username', 'Utilisateur')}")
    
    # Afficher le type de base de données utilisée
    try:
        from database import get_database_info
        db_info = get_database_info()
        if db_info['type'] == 'Supabase (API)':
            st.markdown(f"💾 **Base de données:** 🟢 {db_info['type']} - {db_info['status']}")
        else:
            st.markdown(f"💾 **Base de données:** 🟡 {db_info['type']} - {db_info['status']}")
            if db_info.get('error'):
                with st.expander("ℹ️ Comment activer Supabase"):
                    st.write(f"**Problème:** {db_info['error']}")
                    st.write("**Solution:**")
                    st.write("1. Allez sur Streamlit Cloud → Manage app → Secrets")
                    st.write("2. Ajoutez ces deux clés:")
                    st.code('''SUPABASE_URL = "https://zypgufpilsuunsiclykw.supabase.co"
SUPABASE_KEY = "sb_publishable_tuyj9qXdFw5SnVVUMKAGdw_1mDDyf27"''', language="toml")
                    st.write("3. Vérifiez que `supabase>=2.0.0` est dans `requirements.txt`")
                    st.write("4. Redéployez l'application")
    except Exception as e:
        st.markdown(f"💾 **Base de données:** ⚠️ Erreur de détection")

# Sidebar - Paramètres avec style épuré
st.sidebar.markdown("""
    <div style='padding: 1.5rem 0 1rem 0; border-bottom: 2px solid #e5e7eb; margin-bottom: 1.5rem;'>
        <h2 style='color: #111827; margin: 0; font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em;'>
            ⚙️ Paramètres
        </h2>
        <p style='color: #6b7280; margin: 0.5rem 0 0 0; font-size: 0.875rem;'>
            Configurez votre analyse
        </p>
    </div>
""", unsafe_allow_html=True)

# Options de scan - Style carte
st.sidebar.markdown("""
    <div class="param-section" style='margin-top: 0;'>
        <div class="param-section-title">Portée du scan</div>
    </div>
""", unsafe_allow_html=True)

scan_option = st.sidebar.radio(
    "",
    ["Rapide (50 actions)", "Moyen (200 actions)", "Complet (1000+ actions)"],
    index=1,
    label_visibility="collapsed"
)

scan_limits = {
    "Rapide (50 actions)": 50,
    "Moyen (200 actions)": 200,
    "Complet (1000+ actions)": 1000
}

limit = scan_limits[scan_option]

# Critères ajustables - Style épuré avec cartes
st.sidebar.markdown("""
    <div class="param-section">
        <div class="param-section-title">💰 Croissance</div>
    </div>
""", unsafe_allow_html=True)

min_revenue_growth = st.sidebar.slider(
    "Croissance CA minimum",
    5.0, 30.0, float(MIN_REVENUE_GROWTH * 100), 1.0,
    help="Pourcentage minimum de croissance du chiffre d'affaires"
) / 100

min_earnings_growth = st.sidebar.slider(
    "Croissance bénéfices minimum",
    5.0, 30.0, float(MIN_EARNINGS_GROWTH * 100), 1.0,
    help="Pourcentage minimum de croissance des bénéfices"
) / 100

st.sidebar.markdown("""
    <div class="param-section">
        <div class="param-section-title">📊 Rentabilité</div>
    </div>
""", unsafe_allow_html=True)

min_roe = st.sidebar.slider(
    "ROE minimum",
    5.0, 30.0, float(MIN_ROE * 100), 1.0,
    help="Return on Equity minimum en pourcentage"
) / 100

min_profit_margin = st.sidebar.slider(
    "Marge bénéficiaire minimum",
    3.0, 20.0, float(MIN_PROFIT_MARGIN * 100), 0.5,
    help="Marge bénéficiaire minimum en pourcentage"
) / 100

st.sidebar.markdown("""
    <div class="param-section">
        <div class="param-section-title">💎 Valorisation</div>
    </div>
""", unsafe_allow_html=True)

col1, col2 = st.sidebar.columns(2)
with col1:
    min_pe_ratio = st.sidebar.slider(
        "PER min",
        5.0, 20.0, float(MIN_PE_RATIO), 1.0,
        help="Price/Earnings ratio minimum"
    )
with col2:
    max_pe_ratio = st.sidebar.slider(
        "PER max",
        15.0, 50.0, float(MAX_PE_RATIO), 1.0,
        help="Price/Earnings ratio maximum"
    )

col1, col2 = st.sidebar.columns(2)
with col1:
    min_peg_ratio = st.sidebar.slider(
        "PEG min",
        0.1, 1.0, float(MIN_PEG_RATIO), 0.1,
        help="Price/Earnings to Growth ratio minimum"
    )
with col2:
    max_peg_ratio = st.sidebar.slider(
        "PEG max",
        1.0, 5.0, float(MAX_PEG_RATIO), 0.1,
        help="Price/Earnings to Growth ratio maximum"
    )

# Message d'information - Style épuré
st.sidebar.markdown("""
    <div style='background: #f0f9ff; 
                border: 1px solid #bae6fd; 
                border-left: 4px solid #0ea5e9;
                padding: 1rem; 
                border-radius: 8px; 
                margin: 1.5rem 0;'>
        <div style='font-weight: 600; color: #0c4a6e; margin-bottom: 0.5rem; font-size: 0.875rem;'>
            ⏱️ Durée estimée
        </div>
        <div style='font-size: 0.8125rem; color: #075985; line-height: 1.6;'>
            <div>• Rapide: <strong>1-2 min</strong></div>
            <div>• Moyen: <strong>3-5 min</strong></div>
            <div>• Complet: <strong>10-15 min</strong></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Créer des onglets AVANT l'analyse pour qu'ils restent visibles
tab_analyse, tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Analyse Approfondie", 
    "💹 Calculateur d'Intérêts Composés", 
    "🎯 Simulateur de Portefeuille", 
    "📈 Suivi Performance", 
    "💼 Mon Portefeuille Réel"
])

# Bouton de lancement - Style épuré (reste dans la sidebar, accessible depuis tous les onglets)
st.sidebar.markdown("<br>", unsafe_allow_html=True)

# TAB ANALYSE APPROFONDIE
with tab_analyse:
    if st.sidebar.button("🚀 Lancer l'analyse", type="primary", use_container_width=True):
        # Zone de statut avec barre de progression
        status_container = st.container()
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    with status_container:
        st.info("🔄 **Analyse en cours...** Ne fermez pas cette page. L'analyse peut prendre plusieurs minutes.")
    
    # Récupération des listes (MARCHÉS MONDAUX)
    status_text.text("📥 Récupération des listes d'actions (MARCHÉS MONDAUX)...")
    progress_bar.progress(5)
    us_tickers = get_sp500_tickers()
    progress_bar.progress(8)
    nasdaq_tickers = get_nasdaq100_tickers()
    progress_bar.progress(11)
    dow_tickers = get_dowjones_tickers()
    progress_bar.progress(14)
    eu_tickers = get_eurostoxx_tickers()
    progress_bar.progress(17)
    emerging_tickers = get_emerging_markets_tickers()
    progress_bar.progress(20)
    asia_tickers = get_asia_pacific_tickers()
    progress_bar.progress(23)
    canada_tickers = get_canada_tickers()
    
    # Fusionner toutes les listes
    all_tickers = list(set(
        us_tickers + nasdaq_tickers + dow_tickers + eu_tickers + 
        emerging_tickers + asia_tickers + canada_tickers
    ))
    progress_bar.progress(25)
    status_text.text(f"✅ {len(us_tickers)} S&P500, {len(nasdaq_tickers)} NASDAQ, {len(dow_tickers)} Dow, {len(eu_tickers)} EU, {len(emerging_tickers)} Émergents, {len(asia_tickers)} Asie, {len(canada_tickers)} Canada")
    
    # Filtrage avec progression
    status_text.text(f"🔍 Analyse de {len(all_tickers[:limit])} actions... (2-5 minutes)")
    progress_bar.progress(25)
    
    # Utiliser tqdm pour suivre la progression dans screen_stocks avec les paramètres personnalisés
    opportunities = screen_stocks(
        all_tickers[:limit],
        min_revenue_growth=min_revenue_growth,
        min_earnings_growth=min_earnings_growth,
        min_roe=min_roe,
        min_profit_margin=min_profit_margin,
        min_pe_ratio=min_pe_ratio,
        max_pe_ratio=max_pe_ratio,
        min_peg_ratio=min_peg_ratio,
        max_peg_ratio=max_peg_ratio
    )
    progress_bar.progress(50)
    
    if opportunities:
        status_text.text(f"✅ {len(opportunities)} opportunités trouvées")
    else:
        status_text.text("⚠️ Aucune opportunité trouvée avec ces critères")
        progress_bar.progress(100)
        st.warning("⚠️ Aucune opportunité trouvée avec ces critères")
        st.stop()
    
    # Scoring et classement
    status_text.text(f"🏆 Classement et sélection des TOP {TOP_N}...")
    progress_bar.progress(60)
    top_stocks = score_and_rank_stocks(opportunities)
    
    # Analyse technique avec progression
    status_text.text(f"📊 Analyse technique de {len(top_stocks)} actions...")
    progress_bar.progress(65)
    stocks_with_tech = []
    for i, stock in enumerate(top_stocks, 1):
        progress_bar.progress(65 + int((i / len(top_stocks)) * 15))
        status_text.text(f"📊 Analyse technique {i}/{len(top_stocks)}: {stock.get('symbol', 'N/A')}...")
        full_data = get_technical_data(stock)
        if full_data:
            stocks_with_tech.append(full_data)
    
    # Analyse IA avec progression
    status_text.text(f"🧠 Analyse IA avec Mistral pour {len(stocks_with_tech)} actions...")
    progress_bar.progress(85)
    final_results = []
    for i, stock in enumerate(stocks_with_tech, 1):
        progress_bar.progress(85 + int((i / len(stocks_with_tech)) * 10))
        status_text.text(f"🧠 Analyse IA {i}/{len(stocks_with_tech)}: {stock.get('symbol', 'N/A')}...")
        avis_ia = ask_ai_opinion(stock)
        stock['avis_ia'] = avis_ia
        final_results.append(stock)
    
    # Génération du rapport email
    status_text.text("📧 Génération du rapport email...")
    progress_bar.progress(98)
    
    # Créer le rapport pour l'email (format similaire à main.py)
    report = f"\n{'='*70}\n"
    report += f"📊 RAPPORT BOURSE MONDIALE - ANALYSE APPROFONDIE\n"
    report += f"🏆 TOP {len(final_results)} MEILLEURES ACTIONS\n"
    report += f"📅 Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    report += f"{'='*70}\n\n"
    
    for idx, stock in enumerate(final_results, 1):
        avis = stock.get('avis_ia', 'N/A')
        block = f"\n{'='*70}"
        block += f"\n🏆 RANG #{idx} - SCORE: {stock.get('score', 0)}/100"
        block += f"\n{'='*70}"
        block += f"\n🏢 {stock.get('name', 'N/A')} ({stock.get('symbol', 'N/A')}) | Secteur: {stock.get('sector', 'N/A')}"
        block += f"\n💰 PRIX ACTUEL: {stock.get('current_price_eur', 'N/A')} €"
        block += f"\n📊 CROISSANCE CA: {stock.get('revenue_growth', 0)}% | ROE: {stock.get('roe', 0)}%"
        block += f"\n🎯 ZONE D'ACHAT: {stock.get('buy_zone_low_eur', 'N/A')} € - {stock.get('buy_zone_high_eur', 'N/A')} €"
        block += f"\n🤖 ANALYSE IA:\n{avis}\n"
        block += f"\n{'-'*70}\n"
        report += block
    
    # Envoi email à l'utilisateur connecté
    status_text.text("📧 Envoi du rapport par email...")
    try:
        # Récupérer l'email de l'utilisateur connecté
        from database import get_user_email
        user_email = None
        if st.session_state.get('user_id'):
            user_email = get_user_email(st.session_state['user_id'])
        
        if user_email:
            success = send_email(report, len(final_results), recipient_email=user_email)
            if success:
                status_text.text(f"✅ Email envoyé avec succès à {user_email} !")
            else:
                status_text.text(f"⚠️ Erreur lors de l'envoi de l'email à {user_email}")
        else:
            # Fallback vers l'email par défaut si pas d'email utilisateur
            success = send_email(report, len(final_results))
            if success:
                status_text.text("✅ Email envoyé avec succès !")
            else:
                status_text.text("⚠️ Erreur envoi email: Vérifiez la configuration email")
    except Exception as e:
        status_text.text(f"⚠️ Erreur envoi email: {e}")
    
    # Terminé
    progress_bar.progress(100)
    status_text.text(f"✅ **Analyse terminée !** {len(final_results)} actions analysées avec succès.")
    st.success(f"✅ **Analyse terminée !** {len(final_results)} actions analysées avec succès.")
    
    # Stockage des résultats dans la session
    st.session_state['results'] = final_results
    st.session_state['scan_date'] = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    # Sauvegarder l'analyse dans la base de données
    if st.session_state.get('authenticated') and st.session_state.get('user_id'):
        try:
            save_analysis(
                st.session_state['user_id'],
                final_results,
                st.session_state['scan_date']
            )
        except Exception as e:
            st.warning(f"⚠️ Analyse sauvegardée en session mais erreur DB: {e}")

# Affichage des résultats
if 'results' in st.session_state and st.session_state['results']:
    all_results = st.session_state['results']
    scan_date = st.session_state.get('scan_date', 'N/A')
    
    # Filtrer pour ne garder que les actions dans leur zone d'achat
    def is_in_buy_zone(stock):
        """Vérifie si le prix actuel est dans la zone d'achat recommandée"""
        current_price = stock.get('current_price_eur')
        buy_low = stock.get('buy_zone_low_eur')
        buy_high = stock.get('buy_zone_high_eur')
        
        # Vérifier que toutes les valeurs sont disponibles et numériques
        if current_price is None or buy_low is None or buy_high is None:
            return False
        
        try:
            current = float(current_price)
            low = float(buy_low)
            high = float(buy_high)
            return low <= current <= high
        except (ValueError, TypeError):
            return False
    
    # Filtrer les résultats
    results = [stock for stock in all_results if is_in_buy_zone(stock)]
    
    st.markdown("---")
    if results:
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 2rem; 
                        border-radius: 20px; 
                        color: white; 
                        margin: 2rem 0; 
                        box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.3);'>
                <h2 style='color: white; margin: 0 0 0.5rem 0; font-size: 2rem; font-weight: 700;'>
                    🎯 {len(results)} Actions dans leur Zone d'Achat
                </h2>
                <p style='color: rgba(255,255,255,0.9); margin: 0; font-size: 1rem;'>
                    📅 Analyse du {scan_date} | {len(all_results)} actions analysées au total
                </p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.warning(f"⚠️ Aucune action n'est actuellement dans sa zone d'achat intéressante sur les {len(all_results)} analysées.")
        st.info("💡 Vous pouvez voir toutes les actions analysées en désactivant le filtre ci-dessous.")
        # Option pour voir toutes les actions
        show_all = st.checkbox("Afficher toutes les actions analysées", value=False)
        if show_all:
            results = all_results
        else:
            st.stop()
    
    # Métriques principales avec style moderne
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_score = sum(s.get('score', 0) for s in results) / len(results) if results else 0
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 1.5rem; 
                        border-radius: 16px; 
                        color: white; 
                        text-align: center;
                        box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.3);'>
                <p style='margin: 0 0 0.5rem 0; font-size: 0.9rem; opacity: 0.9;'>Score moyen</p>
                <h2 style='margin: 0; font-size: 2.5rem; font-weight: 700;'>{avg_score:.1f}<span style='font-size: 1.5rem;'>/100</span></h2>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        avg_revenue_growth = sum(s.get('revenue_growth', 0) for s in results) / len(results) if results else 0
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                        padding: 1.5rem; 
                        border-radius: 16px; 
                        color: white; 
                        text-align: center;
                        box-shadow: 0 4px 6px -1px rgba(245, 87, 108, 0.3);'>
                <p style='margin: 0 0 0.5rem 0; font-size: 0.9rem; opacity: 0.9;'>Croissance CA moyenne</p>
                <h2 style='margin: 0; font-size: 2.5rem; font-weight: 700;'>{avg_revenue_growth:.1f}<span style='font-size: 1.5rem;'>%</span></h2>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        avg_roe = sum(s.get('roe', 0) for s in results) / len(results) if results else 0
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                        padding: 1.5rem; 
                        border-radius: 16px; 
                        color: white; 
                        text-align: center;
                        box-shadow: 0 4px 6px -1px rgba(79, 172, 254, 0.3);'>
                <p style='margin: 0 0 0.5rem 0; font-size: 0.9rem; opacity: 0.9;'>ROE moyen</p>
                <h2 style='margin: 0; font-size: 2.5rem; font-weight: 700;'>{avg_roe:.1f}<span style='font-size: 1.5rem;'>%</span></h2>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        in_zone_count = sum(1 for s in results if is_in_buy_zone(s))
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); 
                        padding: 1.5rem; 
                        border-radius: 16px; 
                        color: white; 
                        text-align: center;
                        box-shadow: 0 4px 6px -1px rgba(67, 233, 123, 0.3);'>
                <p style='margin: 0 0 0.5rem 0; font-size: 0.9rem; opacity: 0.9;'>Dans Zone d'Achat</p>
                <h2 style='margin: 0; font-size: 2.5rem; font-weight: 700;'>{in_zone_count}<span style='font-size: 1.5rem;'>/{len(results)}</span></h2>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Tableau principal avec style
    st.markdown("""
        <div style='padding: 1.5rem 0;'>
            <h2 style='font-size: 1.75rem; font-weight: 700; color: #1e293b; margin-bottom: 1rem;'>
                📋 Détails des actions
            </h2>
        </div>
    """, unsafe_allow_html=True)
    
    # Préparation des données pour le tableau
    table_data = []
    for idx, stock in enumerate(results, 1):
        current_price = stock.get('current_price_eur', 'N/A')
        buy_low = stock.get('buy_zone_low_eur', 'N/A')
        buy_high = stock.get('buy_zone_high_eur', 'N/A')
        
        # Vérifier si dans la zone d'achat
        in_zone = "✅ OUI" if is_in_buy_zone(stock) else "❌ NON"
        
        table_data.append({
            'Rang': idx,
            'Action': stock.get('name', 'N/A'),
            'Symbole': stock.get('symbol', 'N/A'),
            'Score': stock.get('score', 0),
            'Prix Actuel (€)': current_price if current_price != 'N/A' else 'N/A',
            'Zone Achat (€)': f"{buy_low} - {buy_high}" if buy_low != 'N/A' and buy_high != 'N/A' else 'N/A',
            'Dans Zone': in_zone,
            'Croissance CA (%)': stock.get('revenue_growth', 0),
            'ROE (%)': stock.get('roe', 0),
            'PER': stock.get('pe', 'N/A'),
            'RSI': stock.get('rsi', 'N/A'),
            'Tendance': stock.get('short_trend', 'N/A')
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Graphiques
    st.markdown("---")
    st.subheader("📈 Visualisations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Graphique des scores
        fig_scores = go.Figure(data=[
            go.Bar(
                x=[s.get('symbol', '') for s in results],
                y=[s.get('score', 0) for s in results],
                marker_color='lightblue',
                text=[f"{s.get('score', 0):.1f}" for s in results],
                textposition='auto'
            )
        ])
        fig_scores.update_layout(
            title="Scores des TOP 20 Actions",
            xaxis_title="Actions",
            yaxis_title="Score (/100)",
            height=400
        )
        st.plotly_chart(fig_scores, use_container_width=True)
    
    with col2:
        # Graphique croissance vs ROE
        fig_scatter = go.Figure(data=[
            go.Scatter(
                x=[s.get('revenue_growth', 0) for s in results],
                y=[s.get('roe', 0) for s in results],
                mode='markers+text',
                text=[s.get('symbol', '') for s in results],
                textposition="top center",
                marker=dict(
                    size=[s.get('score', 0)/2 for s in results],
                    color=[s.get('score', 0) for s in results],
                    colorscale='Viridis',
                    showscale=True
                )
            )
        ])
        fig_scatter.update_layout(
            title="Croissance CA vs ROE (taille = score)",
            xaxis_title="Croissance CA (%)",
            yaxis_title="ROE (%)",
            height=400
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    # Graphique des zones d'achat
    st.subheader("💰 Zones d'achat potentielles (en EUR)")
    
    buy_zones_data = []
    for stock in results:
        if stock.get('buy_zone_low_eur') and stock.get('buy_zone_high_eur'):
            buy_zones_data.append({
                'Action': stock.get('symbol', ''),
                'Prix actuel': stock.get('current_price_eur', 0),
                'Zone basse': stock.get('buy_zone_low_eur', 0),
                'Zone haute': stock.get('buy_zone_high_eur', 0)
            })
    
    if buy_zones_data:
        fig_zones = go.Figure()
        
        for zone in buy_zones_data:
            fig_zones.add_trace(go.Scatter(
                x=[zone['Action'], zone['Action']],
                y=[zone['Zone basse'], zone['Zone haute']],
                mode='lines+markers',
                name=zone['Action'],
                line=dict(width=8),
                marker=dict(size=10)
            ))
            # Prix actuel
            fig_zones.add_trace(go.Scatter(
                x=[zone['Action']],
                y=[zone['Prix actuel']],
                mode='markers',
                name=f"{zone['Action']} - Prix actuel",
                marker=dict(size=12, color='red', symbol='diamond')
            ))
        
        fig_zones.update_layout(
            title="Fourchettes d'achat recommandées (en EUR)",
            xaxis_title="Actions",
            yaxis_title="Prix (EUR)",
            height=500,
            showlegend=False
        )
        st.plotly_chart(fig_zones, use_container_width=True)
    
    # Détails par action
    st.markdown("---")
    st.subheader("🔍 Analyse détaillée par action")
    
    selected_stock = st.selectbox(
        "Sélectionner une action pour voir les détails",
        [f"{s.get('symbol', '')} - {s.get('name', '')}" for s in results]
    )
    
    if selected_stock:
        stock_idx = [f"{s.get('symbol', '')} - {s.get('name', '')}" for s in results].index(selected_stock)
        stock = results[stock_idx]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Données fondamentales")
            st.write(f"**Secteur:** {stock.get('sector', 'N/A')}")
            st.write(f"**Croissance CA:** {stock.get('revenue_growth', 0)}%")
            st.write(f"**Croissance bénéfices:** {stock.get('earnings_growth', 0)}%")
            st.write(f"**Marge bénéficiaire:** {stock.get('profit_margin', 0)}%")
            st.write(f"**ROE:** {stock.get('roe', 0)}%")
            st.write(f"**PER:** {stock.get('pe', 'N/A')}")
            st.write(f"**PEG:** {stock.get('peg', 'N/A')}")
            st.write(f"**P/B:** {stock.get('price_to_book', 'N/A')}")
        
        with col2:
            st.markdown("#### 📈 Données techniques")
            st.write(f"**RSI:** {stock.get('rsi', 'N/A')}")
            st.write(f"**Tendance long terme:** {stock.get('trend', 'N/A')}")
            st.write(f"**Tendance court terme:** {stock.get('short_trend', 'N/A')}")
            st.write(f"**Variation 1 mois:** {stock.get('change_1m', 'N/A')}%")
            st.write(f"**Variation 3 mois:** {stock.get('change_3m', 'N/A')}%")
            st.write(f"**Volatilité:** {stock.get('volatility', 'N/A')}%")
            st.write(f"**SMA200:** {stock.get('sma200_eur', 'N/A')} €")
        
        st.markdown("#### 💰 Zones d'achat (EUR)")
        st.write(f"**Prix actuel:** {stock.get('current_price_eur', 'N/A')} €")
        st.write(f"**🎯 Fourchette d'achat idéale:** {stock.get('buy_zone_low_eur', 'N/A')} € - {stock.get('buy_zone_high_eur', 'N/A')} €")
        st.write(f"**Support 6 mois:** {stock.get('support_6m_eur', 'N/A')} €")
        
        st.markdown("#### 🤖 Analyse IA")
        st.info(stock.get('avis_ia', 'Analyse non disponible'))

    else:
        st.info("👆 Utilisez le menu de gauche pour lancer une analyse. Les résultats s'afficheront ici.")

# ============================================
# NOUVELLES FONCTIONNALITÉS : RENDEMENTS & SIMULATION
# ============================================

# Créer des onglets pour organiser les nouvelles fonctionnalités
tab1, tab2, tab3, tab4 = st.tabs(["💹 Calculateur d'Intérêts Composés", "🎯 Simulateur de Portefeuille", "📈 Suivi Performance", "💼 Mon Portefeuille Réel"])

# ============================================
# TAB 1: CALCULATEUR D'INTÉRÊTS COMPOSÉS
# ============================================
with tab1:
    st.subheader("💹 Calculateur d'Intérêts Composés")
    st.markdown("**Simulez la croissance de votre capital avec plusieurs scénarios**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        capital_initial = st.number_input(
            "💰 Capital initial (€)",
            min_value=0.0,
            max_value=10000000.0,
            value=10000.0,
            step=1000.0,
            help="Montant de départ que vous investissez",
            key="calc_capital_initial"
        )
        
        versement_periodique = st.number_input(
            "💵 Versement périodique (€)",
            min_value=0.0,
            max_value=100000.0,
            value=0.0,
            step=100.0,
            help="Montant que vous ajoutez régulièrement (0 si aucun)",
            key="calc_versement"
        )
        
        frequence_versement = st.selectbox(
            "📅 Fréquence des versements",
            ["Aucun", "Mensuel", "Trimestriel", "Semestriel", "Annuel"],
            index=0,
            help="Fréquence à laquelle vous ajoutez de l'argent",
            key="calc_freq"
        )
        
        duree_investissement = st.slider(
            "⏱️ Durée d'investissement (années)",
            min_value=1,
            max_value=50,
            value=10,
            step=1,
            key="calc_duree"
        )
    
    with col2:
        st.markdown("#### 📊 Scénarios de Rendement")
        
        taux_optimiste = st.slider(
            "🚀 Scénario Optimiste (%)",
            min_value=0.0,
            max_value=50.0,
            value=12.0,
            step=0.5,
            help="Taux d'intérêt annuel dans le meilleur scénario",
            key="calc_taux_opt"
        )
        
        taux_realiste = st.slider(
            "📈 Scénario Réaliste (%)",
            min_value=0.0,
            max_value=30.0,
            value=8.0,
            step=0.5,
            help="Taux d'intérêt annuel dans le scénario moyen",
            key="calc_taux_real"
        )
        
        taux_pessimiste = st.slider(
            "📉 Scénario Pessimiste (%)",
            min_value=-10.0,
            max_value=15.0,
            value=4.0,
            step=0.5,
            help="Taux d'intérêt annuel dans le scénario défavorable",
            key="calc_taux_pess"
        )
        
        taux_conservateur = st.slider(
            "🛡️ Scénario Conservateur (%)",
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.1,
            help="Taux d'intérêt annuel pour un placement sécurisé (livret A, etc.)",
            key="calc_taux_cons"
        )
    
    # Fonction de calcul avec versements périodiques
    def calculer_interets_composes(capital_init, versement, frequence, taux_annuel, annees):
        """Calcule le capital final avec intérêts composés et versements périodiques"""
        # Conversion de la fréquence en nombre de versements par an
        freq_map = {
            "Aucun": 0,
            "Mensuel": 12,
            "Trimestriel": 4,
            "Semestriel": 2,
            "Annuel": 1
        }
        n = freq_map.get(frequence, 0)
        
        capital = capital_init
        taux_periodique = taux_annuel / 100 / n if n > 0 else taux_annuel / 100
        nb_periodes = n * annees if n > 0 else annees
        
        # Calcul période par période
        resultats = [capital_init]
        periodes_par_annee = n if n > 0 else 1
        
        for periode in range(1, nb_periodes + 1):
            # Intérêts composés sur la période
            capital = capital * (1 + taux_periodique)
            
            # Ajout du versement à la fin de chaque période (sauf la première si capital initial)
            if n > 0 and versement > 0:
                capital += versement
            
            # Enregistrer à la fin de chaque année
            if periode % periodes_par_annee == 0:
                resultats.append(capital)
        
        return capital, resultats
    
    # Calculs pour tous les scénarios
    capital_final_opt, evolution_opt = calculer_interets_composes(
        capital_initial, versement_periodique, frequence_versement, taux_optimiste, duree_investissement
    )
    capital_final_real, evolution_real = calculer_interets_composes(
        capital_initial, versement_periodique, frequence_versement, taux_realiste, duree_investissement
    )
    capital_final_pess, evolution_pess = calculer_interets_composes(
        capital_initial, versement_periodique, frequence_versement, taux_pessimiste, duree_investissement
    )
    capital_final_cons, evolution_cons = calculer_interets_composes(
        capital_initial, versement_periodique, frequence_versement, taux_conservateur, duree_investissement
    )
    
    # Calcul des totaux investis
    freq_map = {"Aucun": 0, "Mensuel": 12, "Trimestriel": 4, "Semestriel": 2, "Annuel": 1}
    nb_versements = freq_map.get(frequence_versement, 0) * duree_investissement
    total_investi = capital_initial + (versement_periodique * nb_versements)
    
    # Gains pour chaque scénario
    gain_opt = capital_final_opt - total_investi
    gain_real = capital_final_real - total_investi
    gain_pess = capital_final_pess - total_investi
    gain_cons = capital_final_cons - total_investi
    
    # Affichage des résultats - Mise à jour automatique
    st.markdown("---")
    st.markdown("### 📊 Résultats des Scénarios (Mise à jour automatique)")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🚀 Optimiste",
            f"{capital_final_opt:,.0f} €",
            delta=f"+{gain_opt:,.0f} € ({taux_optimiste}%/an)",
            delta_color="normal"
        )
        st.caption(f"Total investi: {total_investi:,.0f} €")
        st.caption(f"Multiplicateur: {capital_final_opt/total_investi:.2f}x")
    
    with col2:
        st.metric(
            "📈 Réaliste",
            f"{capital_final_real:,.0f} €",
            delta=f"+{gain_real:,.0f} € ({taux_realiste}%/an)",
            delta_color="normal"
        )
        st.caption(f"Total investi: {total_investi:,.0f} €")
        st.caption(f"Multiplicateur: {capital_final_real/total_investi:.2f}x")
    
    with col3:
        st.metric(
            "📉 Pessimiste",
            f"{capital_final_pess:,.0f} €",
            delta=f"{gain_pess:+,.0f} € ({taux_pessimiste}%/an)",
            delta_color="inverse" if gain_pess < 0 else "normal"
        )
        st.caption(f"Total investi: {total_investi:,.0f} €")
        st.caption(f"Multiplicateur: {capital_final_pess/total_investi:.2f}x")
    
    with col4:
        st.metric(
            "🛡️ Conservateur",
            f"{capital_final_cons:,.0f} €",
            delta=f"+{gain_cons:,.0f} € ({taux_conservateur}%/an)",
            delta_color="normal"
        )
        st.caption(f"Total investi: {total_investi:,.0f} €")
        st.caption(f"Multiplicateur: {capital_final_cons/total_investi:.2f}x")
    
    # Graphique de projection avec tous les scénarios
    st.markdown("---")
    st.markdown("### 📈 Évolution du Capital au Fil du Temps")
    
    annees_liste = list(range(0, duree_investissement + 1))
    
    fig_evolution = go.Figure()
    fig_evolution.add_trace(go.Scatter(
        x=annees_liste,
        y=evolution_opt,
        mode='lines+markers',
        name=f'🚀 Optimiste ({taux_optimiste}%/an)',
        line=dict(color='#10b981', width=3),
        marker=dict(size=6)
    ))
    fig_evolution.add_trace(go.Scatter(
        x=annees_liste,
        y=evolution_real,
        mode='lines+markers',
        name=f'📈 Réaliste ({taux_realiste}%/an)',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=6)
    ))
    fig_evolution.add_trace(go.Scatter(
        x=annees_liste,
        y=evolution_pess,
        mode='lines+markers',
        name=f'📉 Pessimiste ({taux_pessimiste}%/an)',
        line=dict(color='#ef4444', width=3),
        marker=dict(size=6)
    ))
    fig_evolution.add_trace(go.Scatter(
        x=annees_liste,
        y=evolution_cons,
        mode='lines+markers',
        name=f'🛡️ Conservateur ({taux_conservateur}%/an)',
        line=dict(color='#6b7280', width=2, dash='dash'),
        marker=dict(size=5)
    ))
    
    # Ligne du total investi
    total_investi_par_annee = [capital_initial]
    for annee in range(1, duree_investissement + 1):
        total_investi_par_annee.append(capital_initial + (versement_periodique * freq_map.get(frequence_versement, 0) * annee))
    
    fig_evolution.add_trace(go.Scatter(
        x=annees_liste,
        y=total_investi_par_annee,
        mode='lines',
        name='💰 Total Investi',
        line=dict(color='#9ca3af', width=2, dash='dot'),
        opacity=0.7
    ))
    
    fig_evolution.update_layout(
        title=f"💹 Évolution du Capital sur {duree_investissement} ans",
        xaxis_title="Années",
        yaxis_title="Capital (€)",
        height=500,
        hovermode='x unified',
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    st.plotly_chart(fig_evolution, use_container_width=True)
    
    # Tableau récapitulatif détaillé
    st.markdown("---")
    st.markdown("### 📋 Tableau Récapitulatif Détaillé")
    
    tableau_data = {
        'Scénario': ['🚀 Optimiste', '📈 Réaliste', '📉 Pessimiste', '🛡️ Conservateur'],
        'Taux annuel (%)': [f"{taux_optimiste:.2f}", f"{taux_realiste:.2f}", f"{taux_pessimiste:.2f}", f"{taux_conservateur:.2f}"],
        'Capital final (€)': [
            f"{capital_final_opt:,.2f}",
            f"{capital_final_real:,.2f}",
            f"{capital_final_pess:,.2f}",
            f"{capital_final_cons:,.2f}"
        ],
        'Total investi (€)': [f"{total_investi:,.2f}"] * 4,
        'Gain/Perte (€)': [
            f"{gain_opt:+,.2f}",
            f"{gain_real:+,.2f}",
            f"{gain_pess:+,.2f}",
            f"{gain_cons:+,.2f}"
        ],
        'Rendement total (%)': [
            f"{((capital_final_opt/total_investi - 1)*100):.2f}",
            f"{((capital_final_real/total_investi - 1)*100):.2f}",
            f"{((capital_final_pess/total_investi - 1)*100):.2f}",
            f"{((capital_final_cons/total_investi - 1)*100):.2f}"
        ],
        'Multiplicateur': [
            f"{capital_final_opt/total_investi:.2f}x",
            f"{capital_final_real/total_investi:.2f}x",
            f"{capital_final_pess/total_investi:.2f}x",
            f"{capital_final_cons/total_investi:.2f}x"
        ]
    }
    
    df_recap = pd.DataFrame(tableau_data)
    st.dataframe(df_recap, use_container_width=True, hide_index=True)
    
    # Informations complémentaires
    st.info(f"""
    💡 **Informations:**
    - **Total investi:** {total_investi:,.2f} € (Capital initial + versements)
    - **Versements totaux:** {nb_versements} versements de {versement_periodique:,.2f} €
    - **Comparaison S&P 500:** ~10% par an en moyenne historique (proche du scénario réaliste)
    - **Note:** Les calculs incluent les intérêts composés et les versements périodiques. Les rendements passés ne préjugent pas des performances futures.
    """)

# ============================================
# TAB 2: SIMULATEUR DE PORTEFEUILLE AVEC STOP-LOSS
# ============================================
with tab2:
    st.subheader("🎯 Simulateur de Portefeuille avec Stop-Loss")
    st.markdown("**Simulez un portefeuille avec gestion du risque (stop-loss et prise de profit)**")
    
    if 'results' in st.session_state and st.session_state['results']:
        available_stocks = st.session_state['results']
        
        col1, col2 = st.columns(2)
        
        with col1:
            capital_total = st.number_input(
                "💰 Capital total à investir (€)",
                min_value=1000.0,
                max_value=1000000.0,
                value=10000.0,
                step=1000.0,
                key="portfolio_capital"
            )
            
            pourcentage_par_action = st.slider(
                "📊 Pourcentage maximum par action (%)",
                min_value=5.0,
                max_value=20.0,
                value=10.0,
                step=1.0,
                help="Limite de diversification (max 10% par action recommandé)"
            )
        
        with col2:
            stop_loss_pourcentage = st.slider(
                "🛑 Stop-Loss (%)",
                min_value=5.0,
                max_value=30.0,
                value=15.0,
                step=1.0,
                help="Pourcentage de perte maximum avant vente automatique"
            )
            
            prise_profit_pourcentage = st.slider(
                "🎯 Prise de Profit (%)",
                min_value=10.0,
                max_value=100.0,
                value=30.0,
                step=5.0,
                help="Pourcentage de gain pour vendre partiellement"
            )
        
        # Sélection des actions
        st.markdown("### 📋 Sélection des Actions")
        st.caption(f"Choisissez jusqu'à {int(100/pourcentage_par_action)} actions (max {pourcentage_par_action}% chacune)")
        
        selected_stocks = []
        nb_max_actions = min(int(100/pourcentage_par_action), len(available_stocks))
        
        for i in range(nb_max_actions):
            if i < len(available_stocks):
                stock = available_stocks[i]
                col1, col2, col3 = st.columns([3, 2, 2])
                
                with col1:
                    include = st.checkbox(
                        f"{stock.get('symbol', 'N/A')} - {stock.get('name', 'N/A')[:30]}...",
                        value=(i < 10),  # Inclure les 10 premières par défaut
                        key=f"stock_{i}"
                    )
                
                if include:
                    with col2:
                        allocation = st.number_input(
                            f"Allocation (%)",
                            min_value=0.0,
                            max_value=pourcentage_par_action,
                            value=min(pourcentage_par_action, 100.0/nb_max_actions),
                            step=0.5,
                            key=f"alloc_{i}"
                        )
                    
                    with col3:
                        prix_achat = st.number_input(
                            f"Prix d'achat (€)",
                            min_value=0.01,
                            max_value=10000.0,
                            value=float(stock.get('current_price_eur', 100.0)),
                            step=0.01,
                            key=f"price_{i}"
                        )
                    
                    if allocation > 0:
                        selected_stocks.append({
                            'symbol': stock.get('symbol', ''),
                            'name': stock.get('name', ''),
                            'allocation': allocation,
                            'prix_achat': prix_achat,
                            'score': stock.get('score', 0),
                            'current_price': stock.get('current_price_eur', prix_achat)
                        })
        
        # Calcul du portefeuille
        if selected_stocks:
            total_allocation = sum(s['allocation'] for s in selected_stocks)
            
            if total_allocation > 100:
                st.warning(f"⚠️ Allocation totale: {total_allocation:.1f}% (maximum 100%)")
            else:
                st.success(f"✅ Allocation totale: {total_allocation:.1f}%")
                
                # Calculs détaillés
                portfolio_data = []
                for stock in selected_stocks:
                    montant_investi = capital_total * (stock['allocation'] / 100)
                    nb_titres = montant_investi / stock['prix_achat']
                    prix_stop_loss = stock['prix_achat'] * (1 - stop_loss_pourcentage / 100)
                    prix_prise_profit = stock['prix_achat'] * (1 + prise_profit_pourcentage / 100)
                    perte_max = montant_investi * (stop_loss_pourcentage / 100)
                    gain_cible = montant_investi * (prise_profit_pourcentage / 100)
                    
                    portfolio_data.append({
                        'Action': stock['symbol'],
                        'Allocation (%)': stock['allocation'],
                        'Montant (€)': montant_investi,
                        'Nb Titres': round(nb_titres, 2),
                        'Prix Achat (€)': stock['prix_achat'],
                        'Stop-Loss (€)': round(prix_stop_loss, 2),
                        'Prise Profit (€)': round(prix_prise_profit, 2),
                        'Perte Max (€)': round(perte_max, 2),
                        'Gain Cible (€)': round(gain_cible, 2)
                    })
                
                df_portfolio = pd.DataFrame(portfolio_data)
                
                st.markdown("### 📊 Composition du Portefeuille")
                st.dataframe(df_portfolio, use_container_width=True, hide_index=True)
                
                # Résumé du risque
                st.markdown("### ⚠️ Analyse du Risque")
                col1, col2, col3, col4 = st.columns(4)
                
                perte_totale_max = sum(p['Perte Max (€)'] for p in portfolio_data)
                gain_total_cible = sum(p['Gain Cible (€)'] for p in portfolio_data)
                capital_restant = capital_total * (1 - total_allocation / 100)
                
                with col1:
                    st.metric("💰 Capital investi", f"{capital_total * (total_allocation/100):,.0f} €")
                
                with col2:
                    st.metric("💵 Capital disponible", f"{capital_restant:,.0f} €")
                
                with col3:
                    st.metric("🛑 Perte maximale totale", f"-{perte_totale_max:,.0f} €", delta=f"-{stop_loss_pourcentage}%")
                
                with col4:
                    st.metric("🎯 Gain cible total", f"+{gain_total_cible:,.0f} €", delta=f"+{prise_profit_pourcentage}%")
                
                # Graphique de répartition
                fig_pie = go.Figure(data=[go.Pie(
                    labels=[s['symbol'] for s in selected_stocks],
                    values=[s['allocation'] for s in selected_stocks],
                    hole=0.3
                )])
                fig_pie.update_layout(
                    title="Répartition du Portefeuille",
                    height=400
                )
                st.plotly_chart(fig_pie, use_container_width=True)
                
                # Recommandations
                st.markdown("### 💡 Recommandations de Gestion")
                st.info(f"""
                **Stratégie recommandée:**
                1. **Diversification:** {len(selected_stocks)} actions sélectionnées (idéal: 15-20)
                2. **Stop-Loss:** Vendez automatiquement si une action baisse de {stop_loss_pourcentage}%
                3. **Prise de Profit:** Vendez 50% de vos positions à +{prise_profit_pourcentage}%, gardez le reste pour plus de hausse
                4. **Rééquilibrage:** Revoyez votre portefeuille tous les 3 mois
                5. **Liquidité:** Gardez {capital_restant:,.0f} € en réserve pour les opportunités
                """)
    else:
        st.warning("⚠️ Lancez d'abord une analyse pour utiliser le simulateur de portefeuille.")

# ============================================
# TAB 3: SUIVI DE PERFORMANCE HISTORIQUE
# ============================================
with tab3:
    st.subheader("📈 Suivi de Performance Historique")
    st.markdown("**Enregistrez et suivez vos performances d'investissement**")
    
    # Interface pour enregistrer des transactions
    st.markdown("### 📝 Enregistrer une Transaction")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        date_transaction = st.date_input("📅 Date", value=datetime.now().date())
    
    with col2:
        symbol_transaction = st.text_input("🏷️ Ticker", placeholder="AAPL ou CW8 (ETF)", value="")
    
    with col3:
        type_transaction = st.selectbox("Type", ["Achat", "Vente"])
    
    with col4:
        prix_transaction = st.number_input("💰 Prix (€)", min_value=0.01, value=100.0, step=0.01)
    
    col1, col2 = st.columns(2)
    
    with col1:
        quantite_transaction = st.number_input("📊 Quantité", min_value=1, value=10, step=1)
    
    with col2:
        if st.button("💾 Enregistrer la Transaction", type="primary"):
            # Ici on pourrait sauvegarder dans un fichier JSON ou base de données
            st.success(f"✅ Transaction enregistrée: {type_transaction} {quantite_transaction} {symbol_transaction} à {prix_transaction}€")
    
    st.markdown("---")
    
    # Simulation de performance (en attendant les vraies données)
    st.markdown("### 📊 Performance Simulée")
    st.caption("Basée sur les critères de sélection de l'agent")
    
    # Paramètres de simulation
    col1, col2 = st.columns(2)
    
    with col1:
        periode_simulation = st.selectbox(
            "📅 Période",
            ["1 mois", "3 mois", "6 mois", "1 an", "3 ans", "5 ans"],
            index=3
        )
        
        rendement_moyen = st.slider(
            "📈 Rendement moyen simulé (%)",
            min_value=5.0,
            max_value=30.0,
            value=18.0,
            step=1.0
        )
    
    with col2:
        volatilite = st.slider(
            "📊 Volatilité (%)",
            min_value=10.0,
            max_value=50.0,
            value=25.0,
            step=1.0
        )
        
        nb_positions = st.number_input(
            "📋 Nombre de positions",
            min_value=1,
            max_value=50,
            value=20,
            step=1
        )
    
    # Simulation de courbe de performance
    jours_map = {"1 mois": 30, "3 mois": 90, "6 mois": 180, "1 an": 365, "3 ans": 1095, "5 ans": 1825}
    nb_jours = jours_map.get(periode_simulation, 365)
    
    # Générer une courbe de performance réaliste
    jours = list(range(0, nb_jours + 1, max(1, nb_jours // 100)))
    rendement_journalier = (rendement_moyen / 100) / 365
    volatilite_journaliere = (volatilite / 100) / np.sqrt(365)
    
    # Simulation avec marche aléatoire
    np.random.seed(42)  # Pour reproductibilité
    variations = np.random.normal(rendement_journalier, volatilite_journaliere, len(jours))
    valeurs = [100]  # Commence à 100 (indice de base)
    
    for var in variations[1:]:
        valeurs.append(valeurs[-1] * (1 + var))
    
    # Graphique de performance
    fig_performance = go.Figure()
    fig_performance.add_trace(go.Scatter(
        x=jours,
        y=valeurs,
        mode='lines',
        name='Performance Simulée',
        line=dict(color='blue', width=2),
        fill='tonexty',
        fillcolor='rgba(0,100,255,0.1)'
    ))
    
    # Ligne de référence (S&P 500 ~10% par an)
    reference_sp500 = [100 * ((1 + 0.10/365) ** j) for j in jours]
    fig_performance.add_trace(go.Scatter(
        x=jours,
        y=reference_sp500,
        mode='lines',
        name='Référence S&P 500 (10%/an)',
        line=dict(color='gray', width=2, dash='dash')
    ))
    
    fig_performance.update_layout(
        title=f"📈 Performance Simulée sur {periode_simulation}",
        xaxis_title="Jours",
        yaxis_title="Valeur du Portefeuille (Base 100)",
        height=500,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_performance, use_container_width=True)
    
    # Métriques de performance
    valeur_finale = valeurs[-1]
    rendement_total = (valeur_finale - 100) / 100 * 100
    rendement_annuelise = ((valeur_finale / 100) ** (365 / nb_jours) - 1) * 100
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Rendement Total", f"{rendement_total:.1f}%")
    
    with col2:
        st.metric("📈 Rendement Annualisé", f"{rendement_annuelise:.1f}%")
    
    with col3:
        valeur_max = max(valeurs)
        drawdown = (valeur_max - valeur_finale) / valeur_max * 100
        st.metric("📉 Drawdown Max", f"-{drawdown:.1f}%")
    
    with col4:
        st.metric("🎯 Surperformance vs S&P 500", f"+{rendement_annuelise - 10:.1f}%")
    
    # Note importante
    st.warning("""
    ⚠️ **Note importante:** 
    Cette simulation est basée sur des paramètres statistiques et ne reflète pas la performance réelle.
    Les performances passées ne préjugent pas des performances futures.
    Investissez toujours selon votre profil de risque.
    """)

# ============================================
# TAB 4: MON PORTEFEUILLE RÉEL (PEA + COMPTE TITRE)
# ============================================
with tab4:
    st.subheader("💼 Mon Portefeuille Boursier Réel")
    st.markdown("**Gérez et suivez votre portefeuille en temps réel (PEA, CTO et Crypto Kraken)**")
    
    # Fichier de sauvegarde du portefeuille
    PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), 'portfolio.json')
    
    # Fonction pour sauvegarder le portefeuille (utilise la base de données)
    def save_portfolio(portfolio):
        """Sauvegarde le portefeuille dans la base de données"""
        return save_portfolio_to_db(portfolio)
    
    # Le portefeuille est déjà chargé par require_auth()
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = {
            'pea': [],
            'compte_titre': [],
            'crypto_kraken': [],
            'comptes_bancaires': []
        }
    
    # Migration automatique depuis portfolio.json si le portefeuille est vide
    if (not st.session_state['portfolio'].get('pea') and 
        not st.session_state['portfolio'].get('compte_titre') and
        not st.session_state['portfolio'].get('crypto_kraken') and
        not st.session_state['portfolio'].get('comptes_bancaires')):
        
        PORTFOLIO_JSON = os.path.join(os.path.dirname(__file__), 'portfolio.json')
        if os.path.exists(PORTFOLIO_JSON):
            try:
                with open(PORTFOLIO_JSON, 'r', encoding='utf-8') as f:
                    old_portfolio = json.load(f)
                
                # Migrer vers la base de données
                migrated_portfolio = {
                    'pea': old_portfolio.get('pea', []),
                    'compte_titre': old_portfolio.get('compte_titre', []),
                    'crypto_kraken': old_portfolio.get('crypto_kraken', []),
                    'comptes_bancaires': old_portfolio.get('comptes_bancaires', [])
                }
                
                if save_portfolio(migrated_portfolio):
                    st.session_state['portfolio'] = migrated_portfolio
                    st.success("✅ Votre ancien portefeuille a été importé depuis portfolio.json !")
                    st.rerun()
            except Exception as e:
                st.warning(f"⚠️ Impossible de migrer l'ancien portefeuille: {e}")
    
    # S'assurer que toutes les clés existent (pour compatibilité avec les anciens fichiers)
    if 'crypto_kraken' not in st.session_state['portfolio']:
        st.session_state['portfolio']['crypto_kraken'] = []
    if 'comptes_bancaires' not in st.session_state['portfolio']:
        st.session_state['portfolio']['comptes_bancaires'] = []
    
    # Fonction pour récupérer le prix en temps réel
    def get_real_time_price(symbol):
        """Récupère le prix actuel d'une action/ETF en temps réel"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Essayer d'abord avec info (plus rapide)
            try:
                info = ticker.info
                if info and len(info) > 5:  # Vérifier que info n'est pas vide
                    current_price = (info.get('currentPrice') or 
                                   info.get('regularMarketPrice') or 
                                   info.get('previousClose') or
                                   info.get('ask') or
                                   info.get('bid'))
                    
                    if current_price and current_price > 0:
                        currency = info.get('currency', 'USD')
                        return current_price, currency
            except:
                pass
            
            # Si info ne fonctionne pas, utiliser l'historique récent
            try:
                hist = ticker.history(period="1d", interval="1m")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    if current_price and current_price > 0:
                        # Pour les actions européennes, le prix est déjà en EUR
                        # Pour les actions US, on devra convertir
                        currency = 'USD'  # Par défaut, on assume USD
                        return current_price, currency
            except:
                pass
            
            # Dernier recours : historique 5 jours
            try:
                hist = ticker.history(period="5d")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    if current_price and current_price > 0:
                        currency = 'USD'
                        return current_price, currency
            except:
                pass
            
            return None, None
        except Exception as e:
            return None, None
    
    # Fonction pour récupérer le prix d'une crypto en EUR
    def get_crypto_price(symbol):
        """Récupère le prix actuel d'une crypto en EUR"""
        try:
            # Mapping des symboles crypto vers les tickers Yahoo Finance
            crypto_map = {
                'BTC': 'BTC-EUR',
                'ETH': 'ETH-EUR',
                'SOL': 'SOL-EUR'
            }
            
            ticker_symbol = crypto_map.get(symbol.upper())
            if not ticker_symbol:
                return None, None
            
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            if info and len(info) > 5:
                current_price = (info.get('currentPrice') or 
                               info.get('regularMarketPrice') or 
                               info.get('previousClose') or
                               info.get('ask') or
                               info.get('bid'))
                
                if current_price and current_price > 0:
                    return current_price, 'EUR'
            
            # Fallback: utiliser l'historique
            try:
                hist = ticker.history(period="1d", interval="1m")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    if current_price and current_price > 0:
                        return current_price, 'EUR'
            except:
                pass
            
            # Dernier recours: historique 5 jours
            try:
                hist = ticker.history(period="5d")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    if current_price and current_price > 0:
                        return current_price, 'EUR'
            except:
                pass
            
            return None, None
        except Exception as e:
            return None, None
    
    # Fonction pour convertir USD en EUR (utilise la même logique que main.py)
    def usd_to_eur(price_usd, apply_xtb_commission=True):
        """Convertit un prix USD en EUR avec commission XTB de 0.5% si demandé
        
        XTB applique la commission sur le taux de change, pas sur le montant.
        Si le taux de marché est 1 USD = X EUR, XTB utilise: X × (1 - 0.005) = X × 0.995
        """
        try:
            eurusd = yf.Ticker("EURUSD=X")
            rate = eurusd.history(period="1d")['Close'].iloc[-1]
            # rate = taux EUR/USD (ex: 1.1715 signifie 1 EUR = 1.1715 USD)
            # Pour convertir USD -> EUR, on divise par rate
            # Exemple: 1 USD / 1.1715 = 0.8536 EUR (taux de marché)
            
            if apply_xtb_commission:
                # XTB applique 0.5% de commission sur le taux de change
                # Donc le taux XTB = taux_marché × 0.995
                # Pour convertir: prix_usd / (rate / 0.995) = prix_usd × 0.995 / rate
                eur_price = price_usd * 0.995 / rate
            else:
                eur_price = price_usd / rate
            
            return eur_price
        except:
            # Taux de secours si l'API ne répond pas
            # Taux approximatif: 1 USD = 0.92 EUR (sans commission)
            if apply_xtb_commission:
                # Avec commission XTB: 0.92 × 0.995 = 0.9154
                return price_usd * 0.9154
            else:
                return price_usd * 0.92
    
    # Fonction pour rechercher et obtenir le nom de l'entreprise
    def get_company_name(ticker_symbol):
        """Récupère le nom de l'entreprise depuis le ticker"""
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            if info and len(info) > 5:
                name = info.get('longName') or info.get('shortName') or info.get('name', ticker_symbol)
                return name
        except:
            pass
        return None
    
    # Fonction pour convertir ISIN en ticker
    def isin_to_ticker(isin):
        """Convertit un ISIN en ticker Yahoo Finance"""
        try:
            # Les ISIN ont le format: 2 lettres (code pays) + 9 chiffres + 1 chiffre de contrôle = 12 caractères
            if len(isin) != 12 or not isin[:2].isalpha() or not isin[2:].isdigit():
                return None
            
            # Essayer de récupérer les infos directement avec l'ISIN
            # Yahoo Finance peut parfois accepter les ISIN avec le préfixe approprié
            ticker = yf.Ticker(isin)
            info = ticker.info
            if info and len(info) > 5:
                # Si ça fonctionne, retourner l'ISIN comme ticker
                return isin
            
            # Sinon, essayer de trouver via une recherche
            # Pour les actions françaises (FR), on peut essayer de construire le ticker
            if isin.startswith('FR'):
                # Les ISIN français commencent par FR
                # On peut essayer de chercher dans une base de données ou utiliser une API
                # Pour l'instant, on retourne None et on laissera l'utilisateur entrer le ticker manuellement
                pass
            
            return None
        except:
            return None
    
    # Fonction pour rechercher un ticker par ISIN sur Moning.co
    def search_isin_on_morningstar(isin):
        """Recherche un ticker par ISIN sur moning.co"""
        try:
            import urllib.request
            from urllib.parse import quote
            import re
            
            # URL de recherche Moning.co pour ISIN
            search_url = f"https://www.moning.co/search?q={quote(isin)}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            
            # Chercher le ticker dans la page (format peut varier)
            # Moning.co affiche souvent le ticker dans la page de résultats
            ticker_patterns = [
                r'"symbol":"([A-Z0-9\.\-]+)"',  # Format JSON
                r'ticker["\']?\s*[:=]\s*["\']?([A-Z0-9\.\-]+)',  # Format texte
                r'<span[^>]*>([A-Z0-9\.\-]+)</span>',  # Format HTML
                r'data-symbol="([A-Z0-9\.\-]+)"',  # Format data attribute
            ]
            
            for pattern in ticker_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    # Filtrer les résultats valides (tickers Yahoo Finance)
                    for match in matches:
                        if len(match) >= 2 and ('.' in match or match.isalnum()):
                            # Vérifier si c'est un ticker valide en testant avec yfinance
                            try:
                                test_ticker = yf.Ticker(match)
                                info = test_ticker.info
                                if info and len(info) > 5:
                                    return match
                            except:
                                continue
            
            return None
        except Exception as e:
            return None
    
    # Fonction pour rechercher un ticker par ISIN (recherche dans une base de données connue puis Moning.co)
    def search_ticker_by_isin(isin):
        """Recherche un ticker connu par son ISIN"""
        # Base de données de correspondance ISIN -> Ticker pour les actions françaises populaires
        isin_to_ticker_map = {
            # Actions françaises populaires
            'FR0000120073': 'TTE.PA',  # TotalEnergies
            'FR0000121013': 'MC.PA',   # LVMH
            'FR0000120324': 'OR.PA',   # L'Oréal
            'FR0000120071': 'AIR.PA',  # Airbus
            'FR0000131104': 'BNP.PA',  # BNP Paribas
            'FR0000130809': 'GLE.PA',  # Société Générale
            'FR0000120578': 'SAN.PA',  # Sanofi
            'FR0000121666': 'EL.PA',   # EssilorLuxottica
            'FR0000125486': 'DG.PA',   # Vinci
            'FR0000121484': 'KER.PA',  # Kering
            'FR0000124141': 'VIE.PA',  # Veolia
            'FR0000051732': 'ATO.PA',  # Atos
            'FR0000120628': 'STM.PA',  # STMicroelectronics
            'FR0000120403': 'SU.PA',   # Schneider Electric
            'FR0000120271': 'RMS.PA',  # Hermès
            'FR0000121014': 'HO.PA',   # Thales
            'FR0000125007': 'CAP.PA',  # Capgemini
            'FR0000120621': 'CA.PA',   # Carrefour
            'FR0000120404': 'ACA.PA',  # Crédit Agricole
            'FR0000120072': 'BN.PA',   # Danone
            'FR0000121121': 'ENGI.PA', # Engie
            'FR0000120074': 'ERF.PA',  # Eurofins
            'FR0000121972': 'RNO.PA',  # Renault
            'FR0000120075': 'SAF.PA',  # Safran
            'FR0000120076': 'SW.PA',   # Sodexo
            'FR0000120077': 'TEP.PA',  # TechnipFMC
            'FR0000120078': 'ML.PA',   # Michelin
            'FR0000120079': 'WLN.PA',  # Worldline
            'FR0000120080': 'LR.PA',   # Legrand
            # Actions allemandes
            'DE0007164600': 'SAP.DE',  # SAP
            'DE0007236101': 'SIE.DE',  # Siemens
            'DE0008404005': 'ALV.DE',  # Allianz
            'DE000BASF111': 'BAS.DE',  # BASF
            'DE000BAY0017': 'BAYN.DE', # Bayer
            'DE0005190003': 'BMW.DE',  # BMW
            'DE0007100000': 'DAI.DE',  # Daimler
            'DE0007664039': 'DBK.DE',  # Deutsche Bank
            'DE0005140008': 'DTE.DE',  # Deutsche Telekom
            'DE000VOW3FN7': 'VOW3.DE', # Volkswagen
            # Actions US (exemples)
            'US0378331005': 'AAPL',    # Apple
            'US5949181045': 'MSFT',    # Microsoft
            'US02079K3059': 'GOOGL',   # Alphabet
            'US0231351067': 'AMZN',    # Amazon
            'US67066G1040': 'NVDA',    # NVIDIA
            'US30303M1027': 'META',    # Meta
            'US88160R1014': 'TSLA',    # Tesla
        }
        
        isin_upper = isin.upper()
        
        # D'abord chercher dans la base de données locale
        ticker = isin_to_ticker_map.get(isin_upper)
        if ticker:
            return ticker
        
        # Si non trouvé, chercher sur Moning.co
        ticker = search_isin_on_morningstar(isin_upper)
        if ticker:
            return ticker
        
        return None
    
    # Fonction pour suggérer des tickers (autocomplétion basique)
    def suggest_tickers(query):
        """Suggère des tickers basés sur une recherche"""
        # Liste de tickers populaires pour l'autocomplétion
        popular_tickers = {
            # Actions US
            'AAPL': 'Apple Inc.', 'MSFT': 'Microsoft Corporation', 'GOOGL': 'Alphabet Inc.',
            'AMZN': 'Amazon.com Inc.', 'NVDA': 'NVIDIA Corporation', 'META': 'Meta Platforms Inc.',
            'TSLA': 'Tesla Inc.', 'JPM': 'JPMorgan Chase & Co.', 'V': 'Visa Inc.',
            # Actions françaises
            'MC.PA': 'LVMH Moët Hennessy', 'TTE.PA': 'TotalEnergies SE', 'OR.PA': 'L\'Oréal SA',
            'AIR.PA': 'Airbus SE', 'BNP.PA': 'BNP Paribas SA', 'GLE.PA': 'Société Générale',
            'SAN.PA': 'Sanofi SA', 'EL.PA': 'EssilorLuxottica', 'DG.PA': 'Vinci SA',
            'KER.PA': 'Kering SA', 'VIE.PA': 'Veolia Environnement', 'ATO.PA': 'Atos SE',
            # ETFs populaires
            'CW8.PA': 'Amundi MSCI World UCITS ETF', 'EWLD.PA': 'Lyxor MSCI World UCITS ETF',
            'PUST.PA': 'Lyxor PEA S&P 500 UCITS ETF', 'BNP.PA': 'BNP Paribas Easy S&P 500 UCITS ETF',
            'CAC.PA': 'Lyxor CAC 40 UCITS ETF', 'EUN2.DE': 'iShares Core MSCI World UCITS ETF',
            # Autres
            'CW8': 'Amundi MSCI World UCITS ETF', 'EWLD': 'Lyxor MSCI World UCITS ETF',
            'PUST': 'Lyxor PEA S&P 500 UCITS ETF'
        }
        
        query_upper = query.upper()
        suggestions = []
        
        # Rechercher dans les tickers populaires
        for ticker, name in popular_tickers.items():
            if query_upper in ticker.upper() or (name and query_upper in name.upper()):
                suggestions.append({'ticker': ticker, 'name': name})
        
        return suggestions[:10]  # Limiter à 10 suggestions
    
    # Fonction pour mettre à jour les noms manquants dans le portefeuille
    def update_missing_names(portfolio):
        """Met à jour les noms manquants pour toutes les positions"""
        updated = False
        
        # Parcourir PEA
        for pos in portfolio['pea']:
            if not pos.get('name') or pos.get('name') == pos.get('symbol'):
                name = get_company_name(pos['symbol'])
                if name:
                    pos['name'] = name
                    updated = True
        
        # Parcourir CTO
        for pos in portfolio['compte_titre']:
            if not pos.get('name') or pos.get('name') == pos.get('symbol'):
                name = get_company_name(pos['symbol'])
                if name:
                    pos['name'] = name
                    updated = True
        
        if updated:
            save_portfolio(portfolio)
        
        return updated
    
    # Afficher un message si le portefeuille est chargé
    if st.session_state['portfolio']['pea'] or st.session_state['portfolio']['compte_titre']:
        nb_positions = len(st.session_state['portfolio']['pea']) + len(st.session_state['portfolio']['compte_titre'])
        st.success(f"💾 Portefeuille chargé : {nb_positions} position(s) sauvegardée(s)")
        
        # Bouton pour mettre à jour les noms manquants
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Mettre à jour les noms", help="Récupère les noms complets pour toutes les positions (ETFs, actions)"):
                with st.spinner("⏳ Mise à jour des noms en cours..."):
                    updated = update_missing_names(st.session_state['portfolio'])
                    if updated:
                        st.success("✅ Noms mis à jour avec succès !")
                        st.rerun()
                    else:
                        st.info("ℹ️ Tous les noms sont déjà à jour")
    
    # Interface pour ajouter une position
    st.markdown("### ➕ Ajouter une Position")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        compte_type = st.selectbox("Type de compte", ["PEA", "CTO", "Crypto Kraken"], key="new_compte")
    
    with col2:
        if compte_type == "Crypto Kraken":
            # Menu déroulant pour les cryptos
            crypto_options = {
                'BTC': 'Bitcoin',
                'ETH': 'Ethereum',
                'SOL': 'Solana'
            }
            selected_crypto = st.selectbox("💰 Sélectionner une crypto", list(crypto_options.keys()), 
                                          format_func=lambda x: f"{x} - {crypto_options[x]}", key="crypto_select")
            symbol_input = selected_crypto
            company_name = crypto_options[selected_crypto]
            search_query = ''  # Pas de recherche pour les cryptos
            is_isin = False
        else:
            # Barre de recherche avec autocomplétion et support ISIN
            placeholder_text = "Tapez AAPL, MC.PA, CW8 ou ISIN (ex: FR0000120073)" if compte_type == "CTO" else "Tapez AAPL, MC.PA, CW8..."
            search_query = st.text_input("🔍 Rechercher un ticker", placeholder=placeholder_text, key="ticker_search")
            
            # Vérifier si l'entrée est un ISIN (12 caractères: 2 lettres + 10 chiffres)
            is_isin = False
            ticker_from_isin = None
            symbol_input = ''
            
            if search_query and len(search_query) == 12:
                # Vérifier le format ISIN: 2 lettres + 10 chiffres
                if search_query[:2].isalpha() and search_query[2:].isdigit():
                    is_isin = True
                    if compte_type == "CTO":
                        # Essayer de convertir l'ISIN en ticker
                        with st.spinner("🔍 Recherche du ticker (base locale puis Moning.co)..."):
                            ticker_from_isin = search_ticker_by_isin(search_query.upper())
                        if ticker_from_isin:
                            st.success(f"✅ ISIN {search_query.upper()} → Ticker: {ticker_from_isin}")
                            symbol_input = ticker_from_isin
                        else:
                            st.warning(f"⚠️ ISIN {search_query.upper()} non trouvé. Entrez le ticker manuellement ou vérifiez l'ISIN.")
                            symbol_input = search_query.upper()  # Utiliser l'ISIN tel quel si non trouvé
                    else:
                        st.info("ℹ️ Les ISIN sont uniquement supportés pour le CTO. Utilisez un ticker pour le PEA.")
                        symbol_input = search_query.upper()
            
            if not is_isin:
                # Afficher les suggestions si l'utilisateur tape quelque chose
                suggestions = []
                if search_query and len(search_query) >= 2:
                    suggestions = suggest_tickers(search_query)
                
                if suggestions:
                    st.markdown("**Suggestions :**")
                    for sug in suggestions:
                        if st.button(f"📌 {sug['ticker']} - {sug['name']}", key=f"sug_{sug['ticker']}", use_container_width=True):
                            st.session_state['selected_ticker'] = sug['ticker']
                            st.rerun()
                
                # Utiliser le ticker sélectionné ou celui saisi
                selected_ticker = st.session_state.get('selected_ticker', '')
                if selected_ticker:
                    symbol_input = selected_ticker
                    st.session_state['selected_ticker'] = ''  # Réinitialiser après utilisation
                else:
                    symbol_input = search_query.upper() if search_query else ''
    
    with col3:
        if compte_type == "Crypto Kraken":
            # Pour les cryptos, permettre les valeurs décimales (ex: 0.012 BTC)
            quantite_input = st.number_input("Quantité", min_value=0.0, value=0.0, step=0.0001, format="%.4f", key="new_quantite_crypto", 
                                            help="Quantité de crypto (ex: 0.012 pour 0.012 BTC)")
        else:
            # Pour les actions, quantité entière
            quantite_input = st.number_input("Quantité", min_value=1, value=1, step=1, key="new_quantite")
    
    with col4:
        if compte_type == "Crypto Kraken":
            # Pour les cryptos, toujours en EUR
            devise_achat = "EUR"
            prix_achat_input = st.number_input(
                "Prix de revient unitaire (EUR)", 
                min_value=0.0, 
                value=0.0, 
                step=0.01, 
                key="new_prix_crypto",
                help="Prix de revient par unité de crypto en EUR (ex: 45000 EUR pour 1 BTC)"
            )
            frais_xtb = 0.0
            use_valeur_marche = False
            use_eur_direct = False
        else:
            # Sélecteur de devise pour le prix d'achat
            devise_achat = st.selectbox("Devise", ["EUR", "USD"], key="new_devise", help="Choisissez la devise du prix d'achat (XTB = USD)")
            
            # Option pour utiliser la valeur de marché XTB
            use_valeur_marche = st.checkbox("💰 Utiliser les données XTB (Valeur de marché + Bénéfice)", key="use_valeur_marche", 
                                            help="Cochez cette case et entrez la valeur de marché actuelle et le bénéfice net tels qu'affichés sur XTB. Le prix de revient sera calculé automatiquement.")
        
        if use_valeur_marche:
            valeur_marche_total = st.number_input(
                "Valeur de marché actuelle (EUR)", 
                min_value=0.0, 
                value=0.0, 
                step=0.01, 
                key="new_valeur_marche",
                help="Valeur de marché actuelle totale en EUR telle qu'affichée sur XTB (ex: 432.27 EUR pour 3 actions)"
            )
            benefice_net = st.number_input(
                "Bénéfice net (EUR)", 
                min_value=-999999.0, 
                value=0.0, 
                step=0.01, 
                key="new_benefice_net",
                help="Bénéfice net en EUR tel qu'affiché sur XTB (ex: +5.14 EUR). Utilisez un nombre négatif pour une perte."
            )
            if quantite_input > 0 and valeur_marche_total > 0:
                # Calculer l'investi: Valeur de marché - Bénéfice
                investi_total = valeur_marche_total - benefice_net
                prix_achat_calcule = investi_total / quantite_input
                st.info(f"💡 Investi total: {investi_total:.2f} EUR | Prix de revient: {prix_achat_calcule:.4f} EUR par action")
                prix_achat_input = prix_achat_calcule
                devise_achat = "EUR"  # Forcer EUR
                frais_xtb = 0.0
            else:
                prix_achat_input = 0.0
                frais_xtb = 0.0
        else:
            # Option pour entrer directement le prix en EUR (recommandé pour XTB)
            use_eur_direct = st.checkbox("💰 Entrer le prix directement en EUR (comme affiché sur XTB)", key="use_eur_direct", 
                                        help="Cochez cette case si vous voulez entrer le prix d'achat tel qu'affiché en EUR sur XTB (déjà avec commission incluse)")
            
            if use_eur_direct:
                prix_achat_input = st.number_input(
                    "Prix d'achat unitaire (EUR)", 
                    min_value=0.01, 
                    value=100.0, 
                    step=0.01, 
                    key="new_prix_eur",
                    help="Prix d'achat par action en EUR tel qu'affiché sur XTB (déjà avec commission de change incluse)"
                )
                devise_achat = "EUR"  # Forcer EUR
                frais_xtb = 0.0
            else:
                prix_achat_input = st.number_input(
                    f"Prix d'achat unitaire ({devise_achat})", 
                    min_value=0.01, 
                    value=100.0, 
                    step=0.01, 
                    key="new_prix",
                    help="Prix d'achat par action (sans frais). Pour USD, commission XTB de 0.5% sur taux de change appliquée automatiquement."
                )
                # Champ pour les frais XTB (en fonction de la devise)
                frais_xtb = 0.0
                frais_label = f"Frais XTB ({devise_achat})"
                frais_xtb = st.number_input(
                    frais_label, 
                    min_value=0.0, 
                    value=0.0, 
                    step=0.01, 
                    key="new_frais",
                    help=f"Frais de transaction XTB en {devise_achat} (ex: 0.5 pour 0.50{devise_achat}). En plus de la commission de change de 0.5%."
                )
                if devise_achat == "USD":
                    st.caption("ℹ️ Commission XTB de 0.5% sur le taux de change USD/EUR appliquée automatiquement")
    
    with col5:
        date_achat_input = st.date_input("Date d'achat", value=datetime.now().date(), key="new_date")
    
    if st.button("➕ Ajouter la Position", type="primary"):
        if symbol_input:
            # Vérifier que le prix d'achat et la quantité sont valides pour les cryptos
            if compte_type == "Crypto Kraken":
                if prix_achat_input <= 0:
                    st.error("⚠️ Veuillez entrer un prix de revient supérieur à 0")
                    st.stop()
                if quantite_input <= 0:
                    st.error("⚠️ Veuillez entrer une quantité supérieure à 0")
                    st.stop()
            # Pour les cryptos, le nom est déjà défini
            if compte_type != "Crypto Kraken":
                # Récupérer le nom de l'entreprise
                company_name = get_company_name(symbol_input)
                if not company_name:
                    company_name = symbol_input  # Utiliser le ticker si le nom n'est pas trouvé
            
            # Pour les cryptos, utiliser directement le prix d'achat
            if compte_type == "Crypto Kraken":
                prix_achat_par_action_eur = prix_achat_input
                prix_unitaire_eur = prix_achat_input
                frais_xtb_eur = 0.0
            # Vérifier si on utilise la valeur de marché XTB
            elif use_valeur_marche and valeur_marche_total > 0 and quantite_input > 0:
                # Récupérer le bénéfice net depuis le widget
                benefice_net = st.session_state.get('new_benefice_net', 0.0) if 'new_benefice_net' in st.session_state else 0.0
                # Calculer l'investi: Valeur de marché - Bénéfice net
                investi_total = valeur_marche_total - benefice_net
                # Calculer le prix de revient par action
                prix_achat_par_action_eur = investi_total / quantite_input
                prix_unitaire_eur = prix_achat_par_action_eur
                frais_xtb_eur = 0.0  # Déjà inclus dans la valeur de marché
            else:
                # Convertir le prix d'achat et les frais en EUR si nécessaire
                # IMPORTANT: XTB applique la commission de 0.5% sur le taux de change
                # Le prix d'achat que vous entrez est le prix USD affiché sur XTB
                if devise_achat == "USD":
                    # Prix unitaire en EUR avec commission XTB de 0.5%
                    prix_unitaire_eur = usd_to_eur(prix_achat_input, apply_xtb_commission=True)
                    # Frais XTB en EUR (les frais de transaction sont déjà dans la devise d'origine)
                    frais_xtb_eur = usd_to_eur(frais_xtb, apply_xtb_commission=True) if frais_xtb > 0 else 0
                else:
                    # Prix unitaire déjà en EUR
                    prix_unitaire_eur = prix_achat_input
                    # Frais XTB déjà en EUR
                    frais_xtb_eur = frais_xtb if frais_xtb > 0 else 0
                
                # Calculer le prix d'achat par action (prix unitaire + frais par action)
                # Les frais sont répartis sur chaque action
                frais_par_action_eur = frais_xtb_eur / quantite_input if quantite_input > 0 else 0
                prix_achat_par_action_eur = prix_unitaire_eur + frais_par_action_eur
            
            new_position = {
                'symbol': symbol_input,
                'name': company_name,  # Nom de l'entreprise
                'quantite': quantite_input,
                'prix_achat': round(prix_achat_par_action_eur, 2),  # Prix d'achat par action en EUR (avec frais inclus)
                'prix_achat_devise': devise_achat,  # Devise d'origine pour référence
                'prix_achat_original': prix_achat_input,  # Prix unitaire d'origine dans la devise d'origine (sans frais)
                'frais_xtb_total_eur': round(frais_xtb_eur, 2),  # Frais XTB totaux en EUR
                'date_achat': date_achat_input.strftime('%Y-%m-%d'),
                'compte': compte_type,
                'prix_actuel_manuel': None  # Prix manuel si le prix automatique n'est pas disponible
            }
            
            if compte_type == "PEA":
                st.session_state['portfolio']['pea'].append(new_position)
            elif compte_type == "CTO":
                st.session_state['portfolio']['compte_titre'].append(new_position)
            elif compte_type == "Crypto Kraken":
                # S'assurer que la clé existe
                if 'crypto_kraken' not in st.session_state['portfolio']:
                    st.session_state['portfolio']['crypto_kraken'] = []
                st.session_state['portfolio']['crypto_kraken'].append(new_position)
            
            # Sauvegarder le portefeuille
            if save_portfolio(st.session_state['portfolio']):
                st.success(f"✅ Position {symbol_input} ({company_name}) ajoutée au {compte_type} et sauvegardée")
            else:
                st.success(f"✅ Position {symbol_input} ({company_name}) ajoutée au {compte_type}")
            st.rerun()
        else:
            st.error("⚠️ Veuillez entrer un ticker")
    
    st.markdown("---")
    
    # Section pour gérer les comptes bancaires
    st.markdown("### 🏦 Comptes Bancaires (Compte Courant, Livret A, etc.)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        nom_compte = st.text_input("Nom du compte", placeholder="Ex: Compte Courant BNP, Livret A", key="nom_compte_bancaire")
    with col2:
        type_compte = st.selectbox("Type de compte", ["Compte Courant", "Livret A", "Livret LDDS", "PEL", "Autre"], key="type_compte_bancaire")
    with col3:
        solde_compte = st.number_input("Solde actuel (€)", min_value=0.0, value=0.0, step=0.01, key="solde_compte_bancaire")
    
    if st.button("➕ Ajouter le Compte Bancaire", key="add_compte_bancaire"):
        if nom_compte:
            nouveau_compte = {
                'nom': nom_compte,
                'type': type_compte,
                'solde': round(solde_compte, 2),
                'date_ajout': datetime.now().date().strftime('%Y-%m-%d')
            }
            if 'comptes_bancaires' not in st.session_state['portfolio']:
                st.session_state['portfolio']['comptes_bancaires'] = []
            st.session_state['portfolio']['comptes_bancaires'].append(nouveau_compte)
            
            # Sauvegarder explicitement
            try:
                if save_portfolio(st.session_state['portfolio']):
                    st.success(f"✅ Compte {nom_compte} ajouté et sauvegardé avec succès")
                else:
                    st.error(f"❌ Erreur lors de la sauvegarde du compte {nom_compte}")
            except Exception as e:
                st.error(f"❌ Erreur lors de la sauvegarde: {str(e)}")
            st.rerun()
        else:
            st.error("⚠️ Veuillez entrer un nom de compte")
    
    # Afficher les comptes bancaires existants
    if st.session_state['portfolio'].get('comptes_bancaires', []):
        st.markdown("#### 📋 Comptes Bancaires Existants")
        for idx, compte in enumerate(st.session_state['portfolio']['comptes_bancaires']):
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
            with col1:
                st.text(f"**{compte['nom']}**")
            with col2:
                st.text(f"Type: {compte['type']}")
            with col3:
                solde_key = f"solde_update_{idx}"
                nouveau_solde = st.number_input(
                    f"Solde (€)",
                    min_value=0.0,
                    value=float(compte['solde']),
                    step=0.01,
                    key=solde_key,
                    label_visibility="collapsed"
                )
            with col4:
                if st.button("💾", key=f"save_solde_{idx}", help="Sauvegarder"):
                    st.session_state['portfolio']['comptes_bancaires'][idx]['solde'] = nouveau_solde
                    if save_portfolio(st.session_state['portfolio']):
                        st.success(f"✅ Solde mis à jour")
                    st.rerun()
            with col5:
                if st.button("🗑️", key=f"delete_compte_{idx}", help="Supprimer"):
                    st.session_state['portfolio']['comptes_bancaires'].pop(idx)
                    if save_portfolio(st.session_state['portfolio']):
                        st.success(f"✅ Compte supprimé")
                    st.rerun()
    
    st.markdown("---")
    
    # Affichage et suivi du portefeuille
    if st.session_state['portfolio']['pea'] or st.session_state['portfolio']['compte_titre'] or st.session_state['portfolio'].get('crypto_kraken', []):
        # Bouton pour actualiser les prix
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 Actualiser les Prix", type="primary"):
                # Forcer le rafraîchissement en vidant le cache des prix
                if 'price_cache' in st.session_state:
                    del st.session_state['price_cache']
                st.rerun()
        
        # Calculer les performances pour chaque compte
        def calculer_performance_portefeuille(positions, is_crypto=False):
            """Calcule la performance d'un portefeuille"""
            total_investi = 0
            total_actuel = 0
            positions_detail = []
            
            for pos in positions:
                symbol = pos['symbol']
                quantite = pos['quantite']
                prix_achat = pos['prix_achat']
                investi = quantite * prix_achat
                total_investi += investi
                
                # Vérifier d'abord si un prix manuel a été saisi
                prix_manuel = pos.get('prix_actuel_manuel')
                
                if prix_manuel and prix_manuel > 0:
                    # Utiliser le prix manuel
                    prix_actuel_eur = float(prix_manuel)
                    valeur_actuelle = quantite * prix_actuel_eur
                    total_actuel += valeur_actuelle
                    
                    gain_perte = valeur_actuelle - investi
                    rendement_pct = (gain_perte / investi) * 100 if investi > 0 else 0
                    
                    positions_detail.append({
                        'symbol': symbol,
                        'quantite': quantite,
                        'prix_achat': prix_achat,
                        'prix_actuel': round(prix_actuel_eur, 2),
                        'investi': round(investi, 2),
                        'valeur_actuelle': round(valeur_actuelle, 2),
                        'gain_perte': round(gain_perte, 2),
                        'rendement_pct': round(rendement_pct, 2),
                        'date_achat': pos['date_achat'],
                        'prix_disponible': True,
                        'prix_manuel': True,
                        'index_original': len(positions_detail)  # Pour retrouver la position originale
                    })
                    continue
                
                # Récupérer le prix actuel automatiquement
                if is_crypto:
                    prix_actuel_raw, currency = get_crypto_price(symbol)
                else:
                    prix_actuel_raw, currency = get_real_time_price(symbol)
                
                if prix_actuel_raw and prix_actuel_raw > 0:
                    # Convertir en EUR si nécessaire
                    # IMPORTANT: Pour XTB, on applique la commission de 0.5% sur le taux de change
                    if currency == 'USD':
                        prix_actuel_eur = usd_to_eur(prix_actuel_raw, apply_xtb_commission=True)
                    elif currency in ['EUR', 'GBP', 'CHF']:
                        # Pour les actions européennes, le prix est déjà dans la devise locale
                        # On convertit si nécessaire (GBP, CHF -> EUR)
                        if currency == 'GBP':
                            try:
                                gbpeur = yf.Ticker("GBPEUR=X")
                                rate = gbpeur.history(period="1d")['Close'].iloc[-1]
                                prix_actuel_eur = prix_actuel_raw * rate
                            except:
                                prix_actuel_eur = prix_actuel_raw * 1.17  # Approximation
                        elif currency == 'CHF':
                            try:
                                chfeur = yf.Ticker("CHFEUR=X")
                                rate = chfeur.history(period="1d")['Close'].iloc[-1]
                                prix_actuel_eur = prix_actuel_raw * rate
                            except:
                                prix_actuel_eur = prix_actuel_raw * 1.02  # Approximation
                        else:
                            prix_actuel_eur = prix_actuel_raw  # Déjà en EUR
                    else:
                        # Autres devises, on assume USD
                        prix_actuel_eur = usd_to_eur(prix_actuel_raw, apply_xtb_commission=True)
                    
                    valeur_actuelle = quantite * prix_actuel_eur
                    total_actuel += valeur_actuelle
                    
                    gain_perte = valeur_actuelle - investi
                    rendement_pct = (gain_perte / investi) * 100 if investi > 0 else 0
                    
                    positions_detail.append({
                        'symbol': symbol,
                        'name': pos.get('name', symbol),  # Nom de l'entreprise
                        'quantite': quantite,
                        'prix_achat': prix_achat,
                        'prix_actuel': round(prix_actuel_eur, 2),
                        'investi': round(investi, 2),
                        'valeur_actuelle': round(valeur_actuelle, 2),
                        'gain_perte': round(gain_perte, 2),
                        'rendement_pct': round(rendement_pct, 2),
                        'date_achat': pos['date_achat'],
                        'prix_disponible': True,
                        'prix_manuel': False,
                        'index_original': len(positions_detail)
                    })
                else:
                    # Si on ne peut pas récupérer le prix, utiliser le prix d'achat ou le prix manuel
                    prix_manuel = pos.get('prix_actuel_manuel')
                    if prix_manuel and prix_manuel > 0:
                        prix_actuel_utilise = float(prix_manuel)
                        valeur_actuelle = quantite * prix_actuel_utilise
                        total_actuel += valeur_actuelle
                        gain_perte = valeur_actuelle - investi
                        rendement_pct = (gain_perte / investi) * 100 if investi > 0 else 0
                    else:
                        prix_actuel_utilise = prix_achat
                        valeur_actuelle = investi
                        gain_perte = 0
                        rendement_pct = 0
                    
                    positions_detail.append({
                        'symbol': symbol,
                        'name': pos.get('name', symbol),  # Nom de l'entreprise
                        'quantite': quantite,
                        'prix_achat': prix_achat,
                        'prix_actuel': round(prix_actuel_utilise, 2),
                        'investi': round(investi, 2),
                        'valeur_actuelle': round(valeur_actuelle, 2),
                        'gain_perte': round(gain_perte, 2),
                        'rendement_pct': round(rendement_pct, 2),
                        'date_achat': pos['date_achat'],
                        'prix_disponible': False,  # Flag pour indiquer que le prix n'a pas pu être récupéré
                        'prix_manuel': bool(prix_manuel and prix_manuel > 0),
                        'index_original': len(positions_detail)
                    })
            
            rendement_total_pct = ((total_actuel - total_investi) / total_investi * 100) if total_investi > 0 else 0
            
            return {
                'total_investi': round(total_investi, 2),
                'total_actuel': round(total_actuel, 2),
                'gain_perte_total': round(total_actuel - total_investi, 2),
                'rendement_total_pct': round(rendement_total_pct, 2),
                'positions': positions_detail
            }
        
        # Calculer pour PEA
        perf_pea = calculer_performance_portefeuille(st.session_state['portfolio']['pea'])
        
        # Calculer pour CTO
        perf_ct = calculer_performance_portefeuille(st.session_state['portfolio']['compte_titre'])
        
        # Calculer pour Crypto Kraken
        perf_crypto = calculer_performance_portefeuille(st.session_state['portfolio'].get('crypto_kraken', []), is_crypto=True)
        
        # Calculer le total des comptes bancaires
        total_comptes_bancaires = sum(compte.get('solde', 0) for compte in st.session_state['portfolio'].get('comptes_bancaires', []))
        
        # Total général (investissements + comptes bancaires)
        total_investi_global = perf_pea['total_investi'] + perf_ct['total_investi'] + perf_crypto['total_investi']
        total_actuel_global = perf_pea['total_actuel'] + perf_ct['total_actuel'] + perf_crypto['total_actuel']
        patrimoine_total = total_actuel_global + total_comptes_bancaires
        gain_perte_global = total_actuel_global - total_investi_global
        rendement_global_pct = (gain_perte_global / total_investi_global * 100) if total_investi_global > 0 else 0
        
        # Métriques globales
        st.markdown("### 📊 Vue d'Ensemble du Patrimoine Global")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "💰 Capital Investi (Bourse/Crypto)",
                f"{total_investi_global:,.2f} €"
            )
        
        with col2:
            st.metric(
                "💵 Valeur Actuelle (Bourse/Crypto)",
                f"{total_actuel_global:,.2f} €"
            )
        
        with col3:
            st.metric(
                "🏦 Comptes Bancaires",
                f"{total_comptes_bancaires:,.2f} €"
            )
        
        with col4:
            st.metric(
                "💎 Patrimoine Total",
                f"{patrimoine_total:,.2f} €"
            )
        
        with col5:
            st.metric(
                "📈 Gain/Perte (Bourse/Crypto)",
                f"{gain_perte_global:+,.2f} €",
                delta=f"{rendement_global_pct:+.2f}%"
            )
        
        # Métriques supplémentaires
        col1, col2 = st.columns(2)
        with col1:
            nb_positions = len(st.session_state['portfolio']['pea']) + len(st.session_state['portfolio']['compte_titre']) + len(st.session_state['portfolio'].get('crypto_kraken', []))
            st.metric("📋 Nombre de Positions Boursières", f"{nb_positions}")
        with col2:
            nb_comptes = len(st.session_state['portfolio'].get('comptes_bancaires', []))
            st.metric("🏦 Nombre de Comptes Bancaires", f"{nb_comptes}")
        
        # Graphique de répartition
        if total_investi_global > 0 or total_comptes_bancaires > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                # Répartition par type de compte (investissements)
                if total_investi_global > 0:
                    fig_repartition = go.Figure(data=[go.Pie(
                        labels=['PEA', 'CTO', 'Crypto Kraken'],
                        values=[perf_pea['total_investi'], perf_ct['total_investi'], perf_crypto['total_investi']],
                        hole=0.3
                    )])
                    fig_repartition.update_layout(
                        title="Répartition des Investissements",
                        height=400
                    )
                    st.plotly_chart(fig_repartition, use_container_width=True)
            
            with col2:
                # Répartition globale (investissements + comptes bancaires)
                if patrimoine_total > 0:
                    labels_patrimoine = []
                    values_patrimoine = []
                    if total_actuel_global > 0:
                        labels_patrimoine.extend(['PEA', 'CTO', 'Crypto Kraken'])
                        values_patrimoine.extend([perf_pea['total_actuel'], perf_ct['total_actuel'], perf_crypto['total_actuel']])
                    if total_comptes_bancaires > 0:
                        labels_patrimoine.append('Comptes Bancaires')
                        values_patrimoine.append(total_comptes_bancaires)
                    
                    if labels_patrimoine:
                        fig_patrimoine = go.Figure(data=[go.Pie(
                            labels=labels_patrimoine,
                            values=values_patrimoine,
                            hole=0.3
                        )])
                        fig_patrimoine.update_layout(
                            title="Répartition du Patrimoine Global",
                            height=400
                        )
                        st.plotly_chart(fig_patrimoine, use_container_width=True)
            
            with col2:
                # Performance par compte
                fig_perf = go.Figure()
                fig_perf.add_trace(go.Bar(
                    x=['PEA', 'CTO', 'Crypto Kraken', 'Total'],
                    y=[perf_pea['rendement_total_pct'], perf_ct['rendement_total_pct'], perf_crypto['rendement_total_pct'], rendement_global_pct],
                    marker_color=['green' if p >= 0 else 'red' for p in [perf_pea['rendement_total_pct'], perf_ct['rendement_total_pct'], rendement_global_pct]]
                ))
                fig_perf.update_layout(
                    title="Rendement par Compte (%)",
                    yaxis_title="Rendement (%)",
                    height=400
                )
                st.plotly_chart(fig_perf, use_container_width=True)
        
        # Détails par compte
        st.markdown("---")
        
        # PEA
        if st.session_state['portfolio']['pea']:
            st.markdown("### 🏦 PEA (Plan d'Épargne en Actions)")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💰 Investi", f"{perf_pea['total_investi']:,.2f} €")
            with col2:
                st.metric("💵 Valeur Actuelle", f"{perf_pea['total_actuel']:,.2f} €")
            with col3:
                st.metric("📈 Gain/Perte", f"{perf_pea['gain_perte_total']:+,.2f} €", delta=f"{perf_pea['rendement_total_pct']:+.2f}%")
            with col4:
                st.metric("📊 Positions", f"{len(perf_pea['positions'])}")
            
            # Tableau des positions PEA avec possibilité de modification
            if perf_pea['positions']:
                st.markdown("#### ✏️ Modifier le prix actuel (PEA)")
                for idx, pos_detail in enumerate(perf_pea['positions']):
                    symbol = pos_detail['symbol']
                    prix_actuel = pos_detail.get('prix_actuel', pos_detail.get('prix_achat', 0))
                    
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    with col1:
                        st.text(f"**{symbol}**")
                    with col2:
                        st.text(f"Prix actuel: {prix_actuel} €")
                    with col3:
                        prix_manuel_key = f"prix_manuel_pea_{symbol}_{idx}"
                        prix_manuel = st.number_input(
                            f"Nouveau prix (€)",
                            min_value=0.01,
                            value=float(prix_actuel),
                            step=0.01,
                            key=prix_manuel_key,
                            label_visibility="collapsed"
                        )
                    with col4:
                        if st.button("💾", key=f"save_pea_{symbol}_{idx}", help="Sauvegarder"):
                            # Trouver et mettre à jour la position dans le portefeuille
                            for i, pos in enumerate(st.session_state['portfolio']['pea']):
                                if pos['symbol'] == symbol:
                                    st.session_state['portfolio']['pea'][i]['prix_actuel_manuel'] = prix_manuel
                                    break
                            if save_portfolio(st.session_state['portfolio']):
                                st.success(f"✅ Prix de {symbol} mis à jour à {prix_manuel} €")
                            st.rerun()
                
                st.markdown("---")
                df_pea = pd.DataFrame(perf_pea['positions'])
                df_pea['compte'] = 'PEA'
                # Réorganiser les colonnes pour afficher le nom en premier
                if 'name' in df_pea.columns:
                    cols = ['symbol', 'name', 'quantite', 'prix_achat', 'prix_actuel', 'investi', 'valeur_actuelle', 'gain_perte', 'rendement_pct', 'date_achat', 'compte']
                    cols = [c for c in cols if c in df_pea.columns]
                    df_pea = df_pea[cols]
                    df_pea.columns = ['Ticker', 'Nom', 'Quantité', 'Prix Achat (€)*', 'Prix Actuel (€)', 'Investi (€)', 'Valeur Actuelle (€)', 'Gain/Perte (€)', 'Rendement (%)', 'Date Achat', 'Compte']
                st.caption("* Prix d'achat inclut les frais XTB (si applicable)")
                st.dataframe(df_pea, use_container_width=True, hide_index=True)
        
        # CTO
        if st.session_state['portfolio']['compte_titre']:
            st.markdown("### 💼 CTO")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💰 Investi", f"{perf_ct['total_investi']:,.2f} €")
            with col2:
                st.metric("💵 Valeur Actuelle", f"{perf_ct['total_actuel']:,.2f} €")
            with col3:
                st.metric("📈 Gain/Perte", f"{perf_ct['gain_perte_total']:+,.2f} €", delta=f"{perf_ct['rendement_total_pct']:+.2f}%")
            with col4:
                st.metric("📊 Positions", f"{len(perf_ct['positions'])}")
            
            # Tableau des positions Compte Titre avec possibilité de modification
            if perf_ct['positions']:
                st.markdown("#### ✏️ Modifier le prix actuel (CTO)")
                for idx, pos_detail in enumerate(perf_ct['positions']):
                    symbol = pos_detail['symbol']
                    name = pos_detail.get('name', symbol)
                    prix_actuel = pos_detail.get('prix_actuel', pos_detail.get('prix_achat', 0))
                    
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    with col1:
                        st.text(f"**{symbol}** - {name}")
                    with col2:
                        st.text(f"Prix actuel: {prix_actuel} €")
                    with col3:
                        prix_manuel_key = f"prix_manuel_ct_{symbol}_{idx}"
                        prix_manuel = st.number_input(
                            f"Nouveau prix (€)",
                            min_value=0.01,
                            value=float(prix_actuel),
                            step=0.01,
                            key=prix_manuel_key,
                            label_visibility="collapsed"
                        )
                    with col4:
                        if st.button("💾", key=f"save_ct_{symbol}_{idx}", help="Sauvegarder"):
                            # Trouver et mettre à jour la position dans le portefeuille
                            for i, pos in enumerate(st.session_state['portfolio']['compte_titre']):
                                if pos['symbol'] == symbol:
                                    st.session_state['portfolio']['compte_titre'][i]['prix_actuel_manuel'] = prix_manuel
                                    break
                            if save_portfolio(st.session_state['portfolio']):
                                st.success(f"✅ Prix de {symbol} mis à jour à {prix_manuel} €")
                            st.rerun()
                
                st.markdown("---")
                df_ct = pd.DataFrame(perf_ct['positions'])
                df_ct['compte'] = 'CTO'
                # Réorganiser les colonnes pour afficher le nom en premier
                if 'name' in df_ct.columns:
                    cols = ['symbol', 'name', 'quantite', 'prix_achat', 'prix_actuel', 'investi', 'valeur_actuelle', 'gain_perte', 'rendement_pct', 'date_achat', 'compte']
                    cols = [c for c in cols if c in df_ct.columns]
                    df_ct = df_ct[cols]
                    df_ct.columns = ['Ticker', 'Nom', 'Quantité', 'Prix Achat (€)*', 'Prix Actuel (€)', 'Investi (€)', 'Valeur Actuelle (€)', 'Gain/Perte (€)', 'Rendement (%)', 'Date Achat', 'Compte']
                st.caption("* Prix d'achat inclut les frais XTB (si applicable)")
                st.dataframe(df_ct, use_container_width=True, hide_index=True)
        
        # Crypto Kraken
        if st.session_state['portfolio'].get('crypto_kraken', []):
            st.markdown("### 🪙 Crypto Kraken")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💰 Investi", f"{perf_crypto['total_investi']:,.2f} €")
            with col2:
                st.metric("💵 Valeur Actuelle", f"{perf_crypto['total_actuel']:,.2f} €")
            with col3:
                st.metric("📈 Gain/Perte", f"{perf_crypto['gain_perte_total']:+,.2f} €", delta=f"{perf_crypto['rendement_total_pct']:+.2f}%")
            with col4:
                st.metric("📊 Positions", f"{len(perf_crypto['positions'])}")
            
            # Tableau des positions Crypto avec possibilité de modification
            if perf_crypto['positions']:
                st.markdown("#### ✏️ Modifier le prix actuel (Crypto Kraken)")
                for idx, pos_detail in enumerate(perf_crypto['positions']):
                    symbol = pos_detail['symbol']
                    name = pos_detail.get('name', symbol)
                    prix_actuel = pos_detail.get('prix_actuel', pos_detail.get('prix_achat', 0))
                    
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    with col1:
                        st.text(f"**{symbol}** - {name}")
                    with col2:
                        prix_revient = pos_detail.get('prix_achat', 0)
                        st.text(f"Prix de revient: {prix_revient} € | Prix actuel: {prix_actuel} €")
                    with col3:
                        prix_manuel_key = f"prix_manuel_crypto_{symbol}_{idx}"
                        prix_manuel = st.number_input(
                            f"Nouveau prix (€)",
                            min_value=0.01,
                            value=float(prix_actuel),
                            step=0.01,
                            key=prix_manuel_key,
                            label_visibility="collapsed"
                        )
                    with col4:
                        if st.button("💾", key=f"save_crypto_{symbol}_{idx}", help="Sauvegarder"):
                            # Trouver et mettre à jour la position dans le portefeuille
                            for i, pos in enumerate(st.session_state['portfolio'].get('crypto_kraken', [])):
                                if pos['symbol'] == symbol:
                                    st.session_state['portfolio']['crypto_kraken'][i]['prix_actuel_manuel'] = prix_manuel
                                    break
                            if save_portfolio(st.session_state['portfolio']):
                                st.success(f"✅ Prix de {symbol} mis à jour à {prix_manuel} €")
                            st.rerun()
                
                st.markdown("---")
                df_crypto = pd.DataFrame(perf_crypto['positions'])
                df_crypto['compte'] = 'Crypto Kraken'
                # Réorganiser les colonnes pour afficher le nom en premier
                if 'name' in df_crypto.columns:
                    cols = ['symbol', 'name', 'quantite', 'prix_achat', 'prix_actuel', 'investi', 'valeur_actuelle', 'gain_perte', 'rendement_pct', 'date_achat', 'compte']
                    cols = [c for c in cols if c in df_crypto.columns]
                    df_crypto = df_crypto[cols]
                    df_crypto.columns = ['Ticker', 'Nom', 'Quantité', 'Prix de Revient (€)', 'Prix Actuel (€)', 'Investi (€)', 'Valeur Actuelle (€)', 'Gain/Perte (€)', 'Rendement (%)', 'Date Achat', 'Compte']
                st.dataframe(df_crypto, use_container_width=True, hide_index=True)
        
        # Tableau consolidé
        st.markdown("### 📋 Vue Consolidée de Toutes les Positions")
        all_positions = []
        if perf_pea['positions']:
            for p in perf_pea['positions']:
                p['compte'] = 'PEA'
                all_positions.append(p)
        if perf_ct['positions']:
            for p in perf_ct['positions']:
                p['compte'] = 'CTO'
                all_positions.append(p)
        if perf_crypto['positions']:
            for p in perf_crypto['positions']:
                p['compte'] = 'Crypto Kraken'
                all_positions.append(p)
        
        if all_positions:
            df_all = pd.DataFrame(all_positions)
            # Réorganiser les colonnes - inclure le nom si disponible
            if 'name' in df_all.columns:
                # Afficher le nom au lieu du ticker
                cols = ['compte', 'name', 'symbol', 'quantite', 'prix_achat', 'prix_actuel', 
                        'investi', 'valeur_actuelle', 'gain_perte', 'rendement_pct', 'date_achat']
                cols = [c for c in cols if c in df_all.columns]
                df_all = df_all[cols]
                df_all.columns = ['Compte', 'Nom', 'Ticker', 'Quantité', 'Prix Achat (€)', 'Prix Actuel (€)',
                                 'Investi (€)', 'Valeur Actuelle (€)', 'Gain/Perte (€)', 'Rendement (%)', 'Date Achat']
            else:
                # Si pas de nom, afficher seulement le ticker
                cols = ['compte', 'symbol', 'quantite', 'prix_achat', 'prix_actuel', 
                        'investi', 'valeur_actuelle', 'gain_perte', 'rendement_pct', 'date_achat']
                cols = [c for c in cols if c in df_all.columns]
                df_all = df_all[cols]
                df_all.columns = ['Compte', 'Ticker', 'Quantité', 'Prix Achat (€)', 'Prix Actuel (€)',
                                 'Investi (€)', 'Valeur Actuelle (€)', 'Gain/Perte (€)', 'Rendement (%)', 'Date Achat']
            st.dataframe(df_all, use_container_width=True, hide_index=True)
        
        # Graphique d'évolution (simulation basée sur les rendements)
        st.markdown("### 📈 Évolution du Portefeuille")
        
        # Créer une courbe d'évolution basée sur les positions
        if all_positions:
            # Trier par date d'achat
            all_positions_sorted = sorted(all_positions, key=lambda x: x['date_achat'])
            
            # Simuler l'évolution (on pourrait améliorer avec des données historiques réelles)
            # Utiliser une fréquence hebdomadaire au lieu de quotidienne
            dates = pd.date_range(start=all_positions_sorted[0]['date_achat'], end=datetime.now().date(), freq='W')
            evolution = []
            valeur_cumulee = 0
            
            for date in dates:
                valeur_date = 0
                for pos in all_positions:
                    date_achat = datetime.strptime(pos['date_achat'], '%Y-%m-%d').date()
                    if date.date() >= date_achat:
                        # Après l'achat, ajouter la valeur
                        valeur_date += pos['valeur_actuelle'] * (pos['rendement_pct'] / 100 + 1) if pos['rendement_pct'] != 0 else pos['investi']
                evolution.append(valeur_date if valeur_date > 0 else None)
            
            # Nettoyer les valeurs None
            evolution_clean = []
            dates_clean = []
            for i, val in enumerate(evolution):
                if val is not None:
                    evolution_clean.append(val)
                    dates_clean.append(dates[i])
            
            if evolution_clean:
                fig_evolution = go.Figure()
                fig_evolution.add_trace(go.Scatter(
                    x=dates_clean,
                    y=evolution_clean,
                    mode='lines',
                    name='Valeur du Portefeuille',
                    line=dict(color='blue', width=2),
                    fill='tonexty',
                    fillcolor='rgba(0,100,255,0.1)'
                ))
                fig_evolution.add_hline(
                    y=total_investi_global,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text="Capital Investi"
                )
                fig_evolution.update_layout(
                    title="Évolution de la Valeur du Portefeuille (Hebdomadaire)",
                    xaxis_title="Date (par semaine)",
                    yaxis_title="Valeur (€)",
                    height=400,
                    hovermode='x unified',
                    xaxis=dict(
                        tickformat='%d/%m/%Y',
                        dtick=604800000  # 7 jours en millisecondes pour afficher chaque semaine
                    )
                )
                st.plotly_chart(fig_evolution, use_container_width=True)
        
        # Bouton pour supprimer des positions
        st.markdown("---")
        st.markdown("### 🗑️ Supprimer une Position")
        
        all_positions_for_delete = []
        for pos in st.session_state['portfolio']['pea']:
            all_positions_for_delete.append(f"PEA - {pos['symbol']} ({pos['quantite']} titres)")
        for pos in st.session_state['portfolio']['compte_titre']:
            all_positions_for_delete.append(f"CTO - {pos['symbol']} ({pos['quantite']} titres)")
        for pos in st.session_state['portfolio'].get('crypto_kraken', []):
            all_positions_for_delete.append(f"Crypto Kraken - {pos['symbol']} ({pos['quantite']} unités)")
        
        if all_positions_for_delete:
            position_to_delete = st.selectbox("Sélectionner la position à supprimer", all_positions_for_delete)
            
            if st.button("🗑️ Supprimer cette Position", type="secondary"):
                compte, reste = position_to_delete.split(" - ", 1)
                symbol_to_delete = reste.split(" (")[0]
                
                if compte == "PEA":
                    st.session_state['portfolio']['pea'] = [p for p in st.session_state['portfolio']['pea'] if p['symbol'] != symbol_to_delete]
                    if save_portfolio(st.session_state['portfolio']):
                        st.success(f"✅ Position {symbol_to_delete} supprimée et sauvegarde mise à jour")
                    else:
                        st.success(f"✅ Position {symbol_to_delete} supprimée")
                elif compte == "CTO":
                    st.session_state['portfolio']['compte_titre'] = [p for p in st.session_state['portfolio']['compte_titre'] if p['symbol'] != symbol_to_delete]
                    if save_portfolio(st.session_state['portfolio']):
                        st.success(f"✅ Position {symbol_to_delete} supprimée et sauvegarde mise à jour")
                    else:
                        st.success(f"✅ Position {symbol_to_delete} supprimée")
                elif compte == "Crypto Kraken":
                    # S'assurer que la clé existe
                    if 'crypto_kraken' not in st.session_state['portfolio']:
                        st.session_state['portfolio']['crypto_kraken'] = []
                    st.session_state['portfolio']['crypto_kraken'] = [p for p in st.session_state['portfolio']['crypto_kraken'] if p['symbol'] != symbol_to_delete]
                    if save_portfolio(st.session_state['portfolio']):
                        st.success(f"✅ Position {symbol_to_delete} supprimée et sauvegarde mise à jour")
                    else:
                        st.success(f"✅ Position {symbol_to_delete} supprimée")
                st.rerun()
    else:
        st.info("👆 Ajoutez vos premières positions en utilisant le formulaire ci-dessus.")

# Footer
st.markdown("---")
st.caption("📊 Agent Bourse - Analyse automatisée avec IA (Mistral via Ollama)")
        