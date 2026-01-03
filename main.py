import os
import sys
import yfinance as yf
import pandas as pd
import smtplib
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️  Ollama non disponible - l'analyse IA sera limitée")
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

# Détecter si on est dans Streamlit
def is_streamlit():
    """Détecte si le code s'exécute dans Streamlit"""
    try:
        import streamlit as st
        return True
    except ImportError:
        return False

# Utiliser tqdm seulement si on n'est pas dans Streamlit
if is_streamlit():
    # Dans Streamlit, on utilise une fonction qui fait juste l'itération
    def tqdm(iterable, desc=None, **kwargs):
        return iterable
else:
    # En dehors de Streamlit, on utilise le vrai tqdm
    from tqdm import tqdm

# Fonctions d'analyse technique (remplacement de pandas_ta)
def calculate_rsi(prices, period=14):
    """Calcule le RSI (Relative Strength Index)"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_sma(prices, period=200):
    """Calcule la moyenne mobile simple (SMA)"""
    return prices.rolling(window=period).mean() 

load_dotenv()

# --- CONFIGURATION ---
EMAIL_SENDER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")
EMAIL_RECEIVER = os.getenv("EMAIL_TARGET")

# Critères de sélection (Filtrage - FONDAMENTAUX SOLIDES + CROISSANCE CA) - DURCIS
MIN_REVENUE_GROWTH = 0.12       # 12% de croissance du chiffre d'affaires minimum (DURCI)
MIN_EARNINGS_GROWTH = 0.10      # 10% de croissance des bénéfices (DURCI)
MAX_PEG_RATIO = 2.0             # PEG < 2.0 (DURCI - meilleur ratio)
MIN_PEG_RATIO = 0.3             # PEG > 0.3 (DURCI)
MAX_PE_RATIO = 30               # PER < 30 (DURCI)
MIN_PE_RATIO = 10               # PER > 10 (DURCI)
MIN_ROE = 0.15                  # ROE > 15% (DURCI - rentabilité très solide)
MIN_PROFIT_MARGIN = 0.08        # Marge bénéficiaire > 8% (DURCI - fondamentaux très solides)

# Limite de scan (augmenté pour analyser plus d'actions)
SCAN_LIMIT = 2000  # Recherche très large et complète

# Nombre d'actions à garder à la fin (TOP 20)
TOP_N = 20

# Filtre Small Caps - Capitalisation boursière minimum (en dollars)
MIN_MARKET_CAP = 2_000_000_000  # 2 milliards USD minimum (exclut les small caps)

# Mode debug (affiche plus d'informations)
DEBUG_MODE = False  # Mettez True pour voir pourquoi les actions sont rejetées 

# --- 1. RÉCUPÉRATION S&P 500 (USA) ---
def get_sp500_tickers():
    print("🇺🇸 Récupération du S&P 500...")
    try:
        # Ajout d'headers pour éviter le blocage 403
        import urllib.request
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read()
        
        table = pd.read_html(html)
        df = table[0]
        # Yahoo Finance utilise des tirets au lieu des points (ex: BRK-B)
        tickers = df['Symbol'].apply(lambda x: x.replace('.', '-')).tolist()
        return tickers
    except Exception as e:
        print(f"⚠️  Erreur S&P 500: {e}")
        print("   Utilisation de la liste de secours...")
        # Liste de secours avec les principales actions du S&P 500
        return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'V', 'JNJ', 
                'WMT', 'MA', 'PG', 'UNH', 'HD', 'DIS', 'BAC', 'ADBE', 'PYPL', 'NFLX',
                'CMCSA', 'PFE', 'KO', 'PEP', 'TMO', 'COST', 'AVGO', 'CSCO', 'ABT', 'MRK',
                'NKE', 'ACN', 'TXN', 'QCOM', 'DHR', 'VZ', 'LIN', 'PM', 'NEE', 'HON',
                'UPS', 'RTX', 'LOW', 'INTU', 'SPGI', 'AMGN', 'DE', 'BKNG', 'AXP', 'SBUX']

# --- 2. RÉCUPÉRATION EURO STOXX 600 (EUROPE) ---
def get_eurostoxx_tickers():
    print("🇪🇺 Récupération de l'Euro Stoxx 600...")
    try:
        # Essai avec plusieurs sources
        import urllib.request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        # Essai 1: Wikipedia EURO_STOXX_600
        try:
            url = 'https://en.wikipedia.org/wiki/EURO_STOXX_600'
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read()
            
            tables = pd.read_html(html)
            if tables and len(tables) > 0:
                df = tables[0]
                tickers = []
                
                # Vérifier les colonnes disponibles
                if 'Ticker' in df.columns:
                    for index, row in df.iterrows():
                        ticker = str(row['Ticker']).strip()
                        if not ticker or ticker == 'nan':
                            continue
                        
                        # Déterminer le suffixe selon le pays
                        row_str = str(row).lower()
                        if 'france' in row_str or 'paris' in row_str or '.pa' in ticker.lower():
                            suffix = ".PA"
                        elif 'germany' in row_str or 'xetra' in row_str or '.de' in ticker.lower():
                            suffix = ".DE"
                        elif 'netherlands' in row_str or 'amsterdam' in row_str or '.as' in ticker.lower():
                            suffix = ".AS"
                        elif 'spain' in row_str or 'madrid' in row_str or '.mc' in ticker.lower():
                            suffix = ".MC"
                        elif 'italy' in row_str or 'milan' in row_str or '.mi' in ticker.lower():
                            suffix = ".MI"
                        elif 'london' in row_str or 'uk' in row_str or '.l' in ticker.lower():
                            suffix = ".L"
                        else:
                            suffix = ""
                        
                        # Ajouter le suffixe si nécessaire
                        if "." not in ticker and suffix:
                            tickers.append(f"{ticker}{suffix}")
                        elif "." in ticker:
                            tickers.append(ticker)
                        elif suffix:
                            tickers.append(f"{ticker}{suffix}")
                
                if len(tickers) > 50:  # Si on a récupéré assez de tickers
                    print(f"   ✅ {len(tickers)} tickers européens récupérés depuis Wikipedia")
                    return tickers
        except Exception as e:
            print(f"   ⚠️  Erreur Wikipedia: {e}")
        
        # Si Wikipedia échoue, utiliser la liste étendue
        print("   Utilisation de la liste de secours étendue (Euro Stoxx 600)...")
        # Liste de secours étendue avec les principales actions européennes
        eu_tickers = [
            # France (CAC 40)
            'MC.PA', 'OR.PA', 'TTE.PA', 'AIR.PA', 'BNP.PA', 'GLE.PA', 'STM.PA', 'SU.PA', 
            'DG.PA', 'EL.PA', 'KER.PA', 'VIE.PA', 'AI.PA', 'ATO.PA', 'CS.PA', 'CAP.PA', 
            'CA.PA', 'ACA.PA', 'BN.PA', 'ENGI.PA', 'ERF.PA', 'RMS.PA', 'RNO.PA', 'SAF.PA', 
            'SAN.PA', 'SW.PA', 'TEP.PA', 'HO.PA', 'FP.PA', 'ML.PA', 'WLN.PA', 'LR.PA',
            # Allemagne (DAX)
            'SAP.DE', 'SIE.DE', 'ALV.DE', 'BAS.DE', 'BAYN.DE', 'BMW.DE', 'CON.DE', '1COV.DE',
            'DAI.DE', 'DBK.DE', 'DPW.DE', 'DTE.DE', 'DWNI.DE', 'EOAN.DE', 'FRE.DE', 'HEN3.DE',
            'IFX.DE', 'LIN.DE', 'MRK.DE', 'MUV2.DE', 'RWE.DE', 'SRT3.DE', 'SY1.DE', 'VOW3.DE',
            'VNA.DE', 'ZAL.DE', 'ADS.DE', 'HEI.DE', 'PAH3.DE',
            # Pays-Bas (AEX)
            'ASML.AS', 'ADYEN.AS', 'INGA.AS', 'PHIA.AS', 'UNA.AS', 'AD.AS', 'AGN.AS', 'AKZA.AS',
            'ASM.AS', 'DSM.AS', 'HEIA.AS', 'IMCD.AS', 'KPN.AS', 'NN.AS', 'RAND.AS', 'REN.AS',
            # Espagne (IBEX 35)
            'SAN.MC', 'BBVA.MC', 'ITX.MC', 'REP.MC', 'TEF.MC', 'IBE.MC', 'FER.MC', 'ENG.MC',
            'CABK.MC', 'ELE.MC', 'GRF.MC', 'IAG.MC', 'MAP.MC', 'MTS.MC', 'NTGY.MC', 'RED.MC',
            # Italie (FTSE MIB)
            'ENEL.MI', 'ENI.MI', 'ISP.MI', 'STLA.MI', 'UCG.MI', 'INTU.MI', 'ATL.MI', 'AZM.MI',
            'BGN.MI', 'BMPS.MI', 'BPE.MI', 'CPR.MI', 'DIA.MI', 'ELN.MI', 'ERG.MI', 'FCA.MI',
            # UK (FTSE 100)
            'GSK.L', 'RIO.L', 'VOD.L', 'BP.L', 'RDSA.L', 'BT.L', 'INTU.L', 'BATS.L', 'BA.L',
            'BARC.L', 'BDEV.L', 'BLND.L', 'BNZL.L', 'BRBY.L', 'CCH.L', 'CPG.L', 'CRDA.L',
            # Suisse
            'NOVN.SW', 'ROG.SW', 'UBSG.SW', 'CSGN.SW', 'NESN.SW', 'ABBN.SW', 'ATLN.SW',
            # Autres pays européens
            'ORSTED.CO', 'DSV.CO', 'CARL-B.CO', 'NOVO-B.CO',  # Danemark
            'EQNR.OL', 'DNB.OL', 'TEL.OL',  # Norvège
            'ASSA-B.ST', 'ATCO-A.ST', 'ATCO-B.ST', 'AZN.ST',  # Suède
        ]
        
        print(f"   ✅ {len(eu_tickers)} tickers européens depuis la liste de secours")
        return eu_tickers
        
    except Exception as e:
        print(f"⚠️  Erreur Euro Stoxx: {e}")
        print("   Utilisation de la liste de secours minimale...")
        # Liste minimale de secours
        return ['MC.PA', 'OR.PA', 'SAP.DE', 'SIE.DE', 'TTE.PA', 'ASML.AS', 'SAN.MC', 'ISP.MI',
                'AIR.PA', 'BNP.PA', 'GLE.PA', 'INGA.AS', 'PHIA.AS', 'BAS.DE', 'BAYN.DE',
                'BMW.DE', 'DAI.DE', 'VOW3.DE', 'ALV.DE', 'MUV2.DE', 'DBK.DE', 'ENEL.MI',
                'ENI.MI', 'STM.PA', 'SU.PA', 'DG.PA', 'EL.PA', 'KER.PA', 'VIE.PA']

# --- 3. RÉCUPÉRATION NASDAQ 100 (USA - Tech & Growth) ---
def get_nasdaq100_tickers():
    print("🇺🇸 Récupération du NASDAQ 100...")
    try:
        import urllib.request
        url = 'https://en.wikipedia.org/wiki/NASDAQ-100'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read()
        
        tables = pd.read_html(html)
        if tables and len(tables) > 0:
            df = tables[0]
            if 'Ticker' in df.columns:
                tickers = df['Ticker'].apply(lambda x: str(x).replace('.', '-')).tolist()
                return tickers
    except Exception as e:
        print(f"   ⚠️  Erreur NASDAQ 100: {e}")
    
    # Liste de secours NASDAQ 100
    return ['AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'COST',
            'NFLX', 'AMD', 'PEP', 'ADBE', 'CSCO', 'CMCSA', 'INTC', 'TXN', 'QCOM', 'INTU',
            'AMGN', 'ISRG', 'AMAT', 'BKNG', 'SBUX', 'ADI', 'VRSK', 'LRCX', 'KLAC', 'SNPS',
            'CDNS', 'CTAS', 'WDAY', 'PAYX', 'NXPI', 'FTNT', 'TEAM', 'ANSS', 'FAST', 'DXCM']

# --- 4. RÉCUPÉRATION DOW JONES (USA - Blue Chips) ---
def get_dowjones_tickers():
    print("🇺🇸 Récupération du Dow Jones...")
    try:
        import urllib.request
        url = 'https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read()
        
        tables = pd.read_html(html)
        if tables and len(tables) > 0:
            df = tables[0]
            if 'Symbol' in df.columns:
                tickers = df['Symbol'].apply(lambda x: str(x).replace('.', '-')).tolist()
                return tickers
    except Exception as e:
        print(f"   ⚠️  Erreur Dow Jones: {e}")
    
    # Liste de secours Dow Jones
    return ['AAPL', 'MSFT', 'UNH', 'GS', 'HD', 'CAT', 'MCD', 'AMGN', 'V', 'HON',
            'TRV', 'AXP', 'IBM', 'JPM', 'WMT', 'CVX', 'MRK', 'PG', 'BA', 'DIS',
            'DOW', 'NKE', 'JNJ', 'CSCO', 'VZ', 'INTC', 'CRM', 'AMZN']

# --- 5. RÉCUPÉRATION PAYS ÉMERGENTS ---
def get_emerging_markets_tickers():
    print("🌍 Récupération des pays émergents...")
    try:
        # Actions des pays émergents (BRICS + autres)
        # Brésil
        brazil_tickers = ['VALE', 'PBR', 'ITUB', 'BBD', 'ABEV', 'SID', 'ERJ', 'GOL']
        
        # Chine (ADR et actions principales)
        china_tickers = ['BABA', 'JD', 'PDD', 'NIO', 'XPEV', 'LI', 'BIDU', 'TME', 'WB', 'BILI',
                         'TAL', 'EDU', 'VIPS', 'YMM', 'TCOM', 'DIDI', 'BZ', 'BEST']
        
        # Inde (ADR)
        india_tickers = ['INFY', 'WIT', 'HDB', 'IBN', 'TTM', 'MINDX', 'INDA']
        
        # Corée du Sud
        korea_tickers = ['005930.KS', '000660.KS', '035420.KS', '051910.KS', '006400.KS']
        
        # Taïwan
        taiwan_tickers = ['TSM', 'UMC', 'ASX', 'CHT']
        
        # Afrique du Sud
        south_africa_tickers = ['SAP', 'NEM', 'GFI', 'ANG']
        
        # Mexique
        mexico_tickers = ['AMX', 'CX', 'TV', 'ASR']
        
        # Turquie
        turkey_tickers = ['TKC', 'AKBNK.IS', 'GARAN.IS']
        
        # Indonésie
        indonesia_tickers = ['BBRI.JK', 'BMRI.JK', 'BBCA.JK']
        
        # Thaïlande
        thailand_tickers = ['PTT.BK', 'KBANK.BK', 'SCB.BK']
        
        all_emerging = (brazil_tickers + china_tickers + india_tickers + korea_tickers +
                        taiwan_tickers + south_africa_tickers + mexico_tickers + 
                        turkey_tickers + indonesia_tickers + thailand_tickers)
        
        return all_emerging
    except Exception as e:
        print(f"   ⚠️  Erreur pays émergents: {e}")
        return ['BABA', 'JD', 'PDD', 'NIO', 'TSM', 'INFY', 'VALE', 'PBR']

# --- 6. RÉCUPÉRATION ASIE-PACIFIQUE (Japon, Australie, etc.) ---
def get_asia_pacific_tickers():
    print("🌏 Récupération de l'Asie-Pacifique...")
    try:
        # Japon (Top 100)
        japan_tickers = ['7203.T', '6758.T', '9984.T', '6861.T', '6098.T', '8035.T', '8306.T',
                        '4503.T', '4063.T', '8058.T', '9434.T', '7267.T', '6501.T', '4568.T',
                        '7741.T', '6954.T', '7974.T', '8801.T', '8411.T', '4661.T']
        
        # Australie (ASX 200 principales)
        australia_tickers = ['CBA.AX', 'WDS.AX', 'BHP', 'RIO', 'ANZ.AX', 'WBC.AX', 'NAB.AX',
                            'TLS.AX', 'CSL.AX', 'FMG.AX', 'GMG.AX', 'WOW.AX', 'STO.AX',
                            'QAN.AX', 'ORG.AX', 'S32.AX', 'WPL.AX', 'OSH.AX']
        
        # Nouvelle-Zélande
        nz_tickers = ['AIA.NZ', 'ANZ.NZ', 'FPH.NZ']
        
        # Singapour
        singapore_tickers = ['D05.SI', 'O39.SI', 'U11.SI', 'Z74.SI']
        
        # Hong Kong
        hk_tickers = ['0700.HK', '0941.HK', '1299.HK', '2318.HK', '1398.HK']
        
        all_asia = (japan_tickers + australia_tickers + nz_tickers + 
                   singapore_tickers + hk_tickers)
        
        return all_asia
    except Exception as e:
        print(f"   ⚠️  Erreur Asie-Pacifique: {e}")
        return ['7203.T', '6758.T', '9984.T', 'CBA.AX', 'BHP', 'RIO']

# --- 7. RÉCUPÉRATION CANADA ---
def get_canada_tickers():
    print("🇨🇦 Récupération du Canada...")
    try:
        # TSX 60 principales
        canada_tickers = ['RY.TO', 'TD.TO', 'BNS.TO', 'CNR.TO', 'CP.TO', 'SHOP.TO', 'BMO.TO',
                         'CM.TO', 'TRP.TO', 'ENB.TO', 'SU.TO', 'IMO.TO', 'CNQ.TO', 'WCN.TO',
                         'ATD.TO', 'L.TO', 'GIB-A.TO', 'CSU.TO', 'MFC.TO', 'SLF.TO']
        return canada_tickers
    except Exception as e:
        print(f"   ⚠️  Erreur Canada: {e}")
        return ['RY.TO', 'TD.TO', 'BNS.TO', 'SHOP.TO']

# --- 4. LE TAMIS (FILTRE) - PRIORITÉ CROISSANCE ET FONDAMENTAUX SOLIDES ---
def screen_stocks(tickers, min_revenue_growth=None, min_earnings_growth=None, min_roe=None, min_profit_margin=None, min_pe_ratio=None, max_pe_ratio=None, min_peg_ratio=None, max_peg_ratio=None):
    import time
    # Utiliser les paramètres personnalisés si fournis, sinon les valeurs par défaut
    if min_revenue_growth is None:
        min_revenue_growth = MIN_REVENUE_GROWTH
    if min_earnings_growth is None:
        min_earnings_growth = MIN_EARNINGS_GROWTH
    if min_roe is None:
        min_roe = MIN_ROE
    if min_profit_margin is None:
        min_profit_margin = MIN_PROFIT_MARGIN
    if min_pe_ratio is None:
        min_pe_ratio = MIN_PE_RATIO
    if max_pe_ratio is None:
        max_pe_ratio = MAX_PE_RATIO
    if min_peg_ratio is None:
        min_peg_ratio = MIN_PEG_RATIO
    if max_peg_ratio is None:
        max_peg_ratio = MAX_PEG_RATIO
    
    candidates = []
    print(f"🕵️  Démarrage du scan sur {len(tickers)} actions...")
    print("📈 Recherche d'entreprises avec CROISSANCE et FONDAMENTAUX SOLIDES...")
    print("☕ Prenez un café, cela peut prendre du temps...")
    
    # Barre de progression
    for ticker in tqdm(tickers[:SCAN_LIMIT], desc="   Analyse"):
        try:
            stock = yf.Ticker(ticker)
            
            # On récupère les infos fondamentales COMPLÈTES (pas fast_info)
            # Cela prend plus de temps mais récupère toutes les données
            info = stock.info
            
            # Vérification que les données sont disponibles
            if not info or len(info) < 10:
                continue
            
            # Prix depuis info (plus fiable)
            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
            if not price or price == 0:
                continue
            
            # Métriques de croissance et fondamentaux
            revenue_growth = info.get('revenueGrowth', None)  # PRIORITÉ: Croissance du CA
            earnings_growth = info.get('earningsGrowth', None)  # Croissance des bénéfices
            peg_ratio = info.get('pegRatio', None)  # Price/Earnings to Growth
            pe_ratio = info.get('trailingPE', None)
            roe = info.get('returnOnEquity', None)  # Return on Equity
            profit_margin = info.get('profitMargins', None)  # Marge bénéficiaire
            
            # Gestion des cas où la donnée est 'None' ou invalide
            if revenue_growth is None: revenue_growth = 0
            if earnings_growth is None: earnings_growth = 0
            if peg_ratio is None: peg_ratio = 999
            if pe_ratio is None: pe_ratio = 999
            if roe is None: roe = 0
            if profit_margin is None: profit_margin = 0
            
            # Le Filtre : PRIORITÉ CROISSANCE CA + FONDAMENTAUX SOLIDES
            # PRIORITÉ 1: Croissance du chiffre d'affaires (critère principal)
            has_revenue_growth = revenue_growth >= min_revenue_growth
            
            # PRIORITÉ 2: Fondamentaux solides (marge bénéficiaire + ROE)
            has_solid_fundamentals = (
                profit_margin >= min_profit_margin and
                roe >= min_roe
            )
            
            # Valorisation raisonnable
            pe_ok = (pe_ratio == 999) or (min_pe_ratio < pe_ratio < max_pe_ratio)
            peg_ok = (peg_ratio == 999) or (min_peg_ratio < peg_ratio < max_peg_ratio)
            
            # On accepte si :
            # - Croissance CA ET (fondamentaux solides OU valorisation raisonnable)
            if has_revenue_growth and (has_solid_fundamentals or (pe_ok and peg_ok)):
                # Croissance CA + (fondamentaux OU valorisation) → accepté
                pass
            elif revenue_growth >= min_revenue_growth * 0.7 and has_solid_fundamentals and pe_ok:
                # Croissance CA modérée + fondamentaux solides → accepté
                pass
            else:
                # Rejeté
                if DEBUG_MODE and ticker in ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'META', 'AMZN']:
                    print(f"\n❌ {ticker} rejeté:")
                    print(f"   Growth CA: {revenue_growth*100:.1f}% (min: {min_revenue_growth*100}%) → {has_revenue_growth}")
                    print(f"   Fondamentaux: Marge={profit_margin*100:.1f}% ROE={roe*100:.1f}% → {has_solid_fundamentals}")
                    print(f"   PER: {pe_ratio if pe_ratio < 999 else 'N/A'} → {pe_ok}")
                    print(f"   PEG: {peg_ratio if peg_ratio < 999 else 'N/A'} → {peg_ok}")
                continue
            
            # Récupération de données fondamentales supplémentaires (AMÉLIORÉ)
            debt_to_equity = info.get('debtToEquity', None)
            current_ratio = info.get('currentRatio', None)  # Liquidité
            price_to_book = info.get('priceToBook', None)  # P/B
            operating_margin = info.get('operatingMargins', None)
            ebitda_margin = info.get('ebitdaMargins', None)
            free_cashflow = info.get('freeCashflow', None)
            market_cap = info.get('marketCap', None)
            
            # NOUVEAUX FACTEURS FONDAMENTAUX
            net_margin = info.get('netProfitMargin', None) or info.get('profitMargins', None)  # Marge nette
            gross_margin = info.get('grossMargins', None)  # Marge brute
            operating_cashflow = info.get('operatingCashflow', None)  # Cash flow opérationnel
            total_revenue = info.get('totalRevenue', None)  # Chiffre d'affaires total
            earnings_per_share = info.get('trailingEps', None) or info.get('forwardEps', None)  # BPA
            book_value = info.get('bookValue', None)  # Valeur comptable
            dividend_yield = info.get('dividendYield', None)  # Rendement dividende
            payout_ratio = info.get('payoutRatio', None)  # Ratio de distribution
            
            # Croissance des bénéfices sur plusieurs périodes
            earnings_quarterly_growth = info.get('earningsQuarterlyGrowth', None)
            earnings_yearly_growth = earnings_growth  # Déjà récupéré
            
            # Ratios de rentabilité supplémentaires
            return_on_assets = info.get('returnOnAssets', None)  # ROA
            return_on_capital = info.get('returnOnCapital', None)  # ROC
            
            # FILTRE SMALL CAPS - Exclure les entreprises avec capitalisation < MIN_MARKET_CAP
            if market_cap is not None and market_cap < MIN_MARKET_CAP:
                if DEBUG_MODE:
                    print(f"   ❌ {ticker} rejeté: Small cap (Market Cap: {market_cap/1_000_000_000:.2f}B < {MIN_MARKET_CAP/1_000_000_000:.0f}B)")
                continue
            
            # Si on arrive ici, l'action passe les critères
            candidates.append({
                "symbol": ticker,
                "name": info.get('longName', ticker),
                "sector": info.get('sector', 'N/A'),
                "price": round(price, 2),
                "revenue_growth": round(revenue_growth * 100, 2) if revenue_growth else 0,
                "earnings_growth": round(earnings_growth * 100, 2) if earnings_growth else 0,
                "earnings_quarterly_growth": round(earnings_quarterly_growth * 100, 2) if earnings_quarterly_growth else None,
                "peg": round(peg_ratio, 2) if peg_ratio < 999 else None,
                "pe": round(pe_ratio, 2) if pe_ratio < 999 else None,
                "roe": round(roe * 100, 2) if roe else 0,
                "profit_margin": round(profit_margin * 100, 2) if profit_margin else 0,
                "net_margin": round(net_margin * 100, 2) if net_margin else None,
                "gross_margin": round(gross_margin * 100, 2) if gross_margin else None,
                "debt_to_equity": round(debt_to_equity, 2) if debt_to_equity else None,
                "current_ratio": round(current_ratio, 2) if current_ratio else None,
                "price_to_book": round(price_to_book, 2) if price_to_book else None,
                "operating_margin": round(operating_margin * 100, 2) if operating_margin else None,
                "ebitda_margin": round(ebitda_margin * 100, 2) if ebitda_margin else None,
                "free_cashflow": free_cashflow,
                "operating_cashflow": operating_cashflow,
                "total_revenue": total_revenue,
                "earnings_per_share": round(earnings_per_share, 2) if earnings_per_share else None,
                "book_value": round(book_value, 2) if book_value else None,
                "dividend_yield": round(dividend_yield * 100, 2) if dividend_yield else None,
                "payout_ratio": round(payout_ratio * 100, 2) if payout_ratio else None,
                "return_on_assets": round(return_on_assets * 100, 2) if return_on_assets else None,
                "return_on_capital": round(return_on_capital * 100, 2) if return_on_capital else None,
                "market_cap": market_cap
            })
            
            # Délai pour éviter de surcharger l'API (ralentit le script mais récupère mieux les données)
            time.sleep(0.1)  # 100ms entre chaque requête
            
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️  Erreur sur {ticker}: {e}")
            continue 
            
    return candidates

# --- 4. SCORING ET CLASSEMENT ---
def score_and_rank_stocks(candidates):
    """Calcule un score pour chaque action et classe les meilleures"""
    scored_stocks = []
    
    for stock in candidates:
        score = 0
        
        # Score croissance CA (40% du score total - PRIORITÉ)
        revenue_growth = stock.get('revenue_growth', 0) / 100
        if revenue_growth >= 0.20:  # > 20%
            score += 40
        elif revenue_growth >= 0.15:  # 15-20%
            score += 35
        elif revenue_growth >= 0.12:  # 12-15%
            score += 30
        else:
            score += revenue_growth * 200  # Proportionnel
        
        # Score croissance bénéfices (20% du score)
        earnings_growth = stock.get('earnings_growth', 0) / 100
        if earnings_growth >= 0.20:  # > 20%
            score += 20
        elif earnings_growth >= 0.15:  # 15-20%
            score += 17
        elif earnings_growth >= 0.10:  # 10-15%
            score += 14
        else:
            score += earnings_growth * 100  # Proportionnel
        
        # Score fondamentaux (25% du score)
        roe = stock.get('roe', 0) / 100
        profit_margin = stock.get('profit_margin', 0) / 100
        
        if roe >= 0.20 and profit_margin >= 0.15:  # Excellents fondamentaux
            score += 25
        elif roe >= 0.15 and profit_margin >= 0.10:
            score += 20
        elif roe >= 0.12 and profit_margin >= 0.08:
            score += 15
        else:
            score += (roe * 100 + profit_margin * 100) / 2  # Moyenne
        
        # Score valorisation (15% du score - meilleur si PEG bas et PER raisonnable)
        pe = stock.get('pe', None)
        peg = stock.get('peg', None)
        
        # Gestion des valeurs None
        if pe is None:
            pe = 999
        if peg is None:
            peg = 999
        
        if pe != 999 and peg != 999:
            if pe < 20 and peg < 1.5:  # Excellente valorisation
                score += 15
            elif pe < 25 and peg < 2.0:
                score += 12
            elif pe < 30 and peg < 2.5:
                score += 8
            else:
                score += 5
        elif pe != 999 and pe < 25:
            score += 10
        else:
            score += 5
        
        stock['score'] = round(score, 2)
        scored_stocks.append(stock)
    
    # Trier par score décroissant et garder les TOP N
    scored_stocks.sort(key=lambda x: x['score'], reverse=True)
    top_stocks = scored_stocks[:TOP_N]
    
    return top_stocks

# --- 5. ANALYSE TECHNIQUE ---
def get_technical_data(candidate):
    try:
        df = yf.download(candidate['symbol'], period="1y", interval="1d", progress=False)
        
        # Vérifie que le DataFrame n'est pas None ou vide
        if df is None or df.empty or len(df) < 200:
            return None
        
        # Gère le MultiIndex si présent
        if isinstance(df.columns, pd.MultiIndex):
            if len(df.columns.levels[0]) == 1:
                df.columns = df.columns.droplevel(0)
            else:
                df.columns = df.columns.droplevel(1)
        
        # S'assure que la colonne Close existe
        if 'Close' not in df.columns:
            return None
        
        # Nettoie les valeurs NaN
        df['Close'] = df['Close'].ffill().bfill()
        if df['Close'].isna().all():
            return None
            
        # Calcul RSI
        rsi_series = calculate_rsi(df['Close'], period=14)
        if rsi_series.empty or rsi_series.isna().all():
            return None
        candidate['rsi'] = round(float(rsi_series.iloc[-1]), 2)
        
        # Calcul SMA200
        sma_series = calculate_sma(df['Close'], period=200)
        if sma_series.empty or sma_series.isna().all():
            return None
        sma = sma_series.iloc[-1]
        
        # Calcul SMA50 (tendance court terme)
        sma50_series = calculate_sma(df['Close'], period=50)
        sma50 = sma50_series.iloc[-1] if not sma50_series.empty else None
        
        price = candidate['price']
        current_price = df['Close'].iloc[-1]
        
        # Vérifie les valeurs NaN
        if pd.isna(candidate['rsi']) or pd.isna(sma):
            return None
        
        # Calcul de la volatilité (écart-type sur 20 jours)
        volatility = df['Close'].tail(20).std() / df['Close'].tail(20).mean() * 100 if len(df) >= 20 else None
        
        # Variation de prix (1 mois, 3 mois, 6 mois)
        price_1m = df['Close'].iloc[-20] if len(df) >= 20 else None
        price_3m = df['Close'].iloc[-60] if len(df) >= 60 else None
        price_6m = df['Close'].iloc[-120] if len(df) >= 120 else None
        
        change_1m = ((current_price - price_1m) / price_1m * 100) if price_1m else None
        change_3m = ((current_price - price_3m) / price_3m * 100) if price_3m else None
        change_6m = ((current_price - price_6m) / price_6m * 100) if price_6m else None
        
        # Volume moyen
        if 'Volume' in df.columns:
            avg_volume = df['Volume'].tail(20).mean() if len(df) >= 20 else None
            recent_volume = df['Volume'].iloc[-1] if not df['Volume'].empty else None
            volume_ratio = (recent_volume / avg_volume) if avg_volume and avg_volume > 0 else None
        else:
            avg_volume = None
            volume_ratio = None
        
        # Détermination de la tendance
        if price > sma:
            trend = "HAUSSIER (Prix > SMA200)"
        else:
            trend = "BAISSIER (Prix < SMA200)"
        
        # Tendance court terme
        if sma50 and current_price > sma50:
            short_trend = "HAUSSIER"
        elif sma50:
            short_trend = "BAISSIER"
        else:
            short_trend = "NEUTRE"
        
        # Calcul des zones d'achat potentielles (support/résistance)
        # Support : minimum des 52 dernières semaines (1 an)
        support_52w = df['Close'].tail(252).min() if len(df) >= 252 else df['Close'].min()
        # Résistance : maximum des 52 dernières semaines
        resistance_52w = df['Close'].tail(252).max() if len(df) >= 252 else df['Close'].max()
        
        # Support à court terme (minimum 3 mois)
        support_3m = df['Close'].tail(60).min() if len(df) >= 60 else support_52w
        # Support à moyen terme (minimum 6 mois)
        support_6m = df['Close'].tail(120).min() if len(df) >= 120 else support_52w
        
        # Niveaux de retracement Fibonacci (si en tendance haussière)
        if current_price > sma:
            # Tendance haussière : calculer les retracements
            high_52w = resistance_52w
            low_52w = support_52w
            range_52w = high_52w - low_52w
            fib_236 = high_52w - (range_52w * 0.236)  # Retracement 23.6%
            fib_382 = high_52w - (range_52w * 0.382)  # Retracement 38.2%
            fib_500 = high_52w - (range_52w * 0.500)  # Retracement 50%
            fib_618 = high_52w - (range_52w * 0.618)  # Retracement 61.8%
        else:
            fib_236 = fib_382 = fib_500 = fib_618 = None
        
        # Zone d'achat optimale : fourchette plus précise pour vision long terme (2-3% au lieu de 5-10%)
        if current_price > sma:
            # Tendance haussière : zone d'achat autour de SMA200 avec fourchette serrée
            buy_zone_low = sma * 0.98  # 2% sous SMA200 (plus précis)
            buy_zone_high = sma * 1.02  # 2% au-dessus SMA200 (plus précis)
        else:
            # Tendance baissière : zone d'achat autour du support 6 mois avec fourchette serrée
            buy_zone_low = support_6m * 0.97  # 3% sous support 6 mois (plus précis)
            buy_zone_high = support_6m * 1.03  # 3% au-dessus support 6 mois (plus précis)
        
        # Récupération du taux de change USD/EUR
        try:
            eur_usd = yf.Ticker("EURUSD=X")
            eur_rate = eur_usd.history(period="1d")['Close'].iloc[-1] if not eur_usd.history(period="1d").empty else 0.92
            # Taux inversé pour convertir USD -> EUR
            usd_to_eur = 1 / eur_rate if eur_rate > 0 else 0.92
        except:
            usd_to_eur = 0.92  # Taux par défaut si erreur
        
        # Conversion en euros
        def usd_to_eur_price(price_usd):
            return round(price_usd * usd_to_eur, 2) if price_usd else None
        
        # Ajout des données techniques enrichies
        candidate['rsi'] = round(float(candidate['rsi']), 2)
        candidate['sma200'] = round(float(sma), 2)
        candidate['sma50'] = round(float(sma50), 2) if sma50 else None
        candidate['trend'] = trend
        candidate['short_trend'] = short_trend
        candidate['volatility'] = round(float(volatility), 2) if volatility else None
        candidate['change_1m'] = round(float(change_1m), 2) if change_1m else None
        candidate['change_3m'] = round(float(change_3m), 2) if change_3m else None
        candidate['change_6m'] = round(float(change_6m), 2) if change_6m else None
        candidate['volume_ratio'] = round(float(volume_ratio), 2) if volume_ratio else None
        candidate['current_price'] = round(float(current_price), 2)
        
        # Zones d'achat potentielles
        candidate['support_52w'] = round(float(support_52w), 2)
        candidate['support_6m'] = round(float(support_6m), 2)
        candidate['resistance_52w'] = round(float(resistance_52w), 2)
        candidate['buy_zone_low'] = round(float(buy_zone_low), 2)
        candidate['buy_zone_high'] = round(float(buy_zone_high), 2)
        candidate['fib_382'] = round(float(fib_382), 2) if fib_382 else None
        candidate['fib_618'] = round(float(fib_618), 2) if fib_618 else None
        
        # Prix en euros
        candidate['current_price_eur'] = usd_to_eur_price(current_price)
        candidate['buy_zone_low_eur'] = usd_to_eur_price(buy_zone_low)
        candidate['buy_zone_high_eur'] = usd_to_eur_price(buy_zone_high)
        candidate['support_6m_eur'] = usd_to_eur_price(support_6m)
        candidate['sma200_eur'] = usd_to_eur_price(sma)
        if fib_382:
            candidate['fib_382_eur'] = usd_to_eur_price(fib_382)
        if fib_618:
            candidate['fib_618_eur'] = usd_to_eur_price(fib_618)
            
        return candidate
    except Exception as e:
        return None

# --- 6. L'AVIS DE L'IA (ANALYSE APPROFONDIE) ---
def ask_ai_opinion(data):
    prompt = f"""
    Tu es un analyste financier expert. Analyse en profondeur cette action avec une analyse TECHNIQUE et FONDAMENTALE détaillée.
    
    ENTREPRISE: {data['name']} ({data['symbol']})
    SECTEUR: {data['sector']}
    PRIX ACTUEL: {data.get('current_price', data.get('price', 0))} $
    
    === ANALYSE FONDAMENTALE ===
    
    CROISSANCE (PRIORITÉ):
    - Croissance CA (1 an): {data.get('revenue_growth', 0)}%
    - Croissance bénéfices (1 an): {data.get('earnings_growth', 0)}%
    
    RENTABILITÉ:
    - Marge bénéficiaire: {data.get('profit_margin', 0)}%
    - ROE (Return on Equity): {data.get('roe', 0)}%
    
    VALORISATION:
    - PER (Price/Earnings): {data.get('pe', 'N/A')}
    - PEG (Price/Earnings to Growth): {data.get('peg', 'N/A')}
    - P/B (Price/Book): {data.get('price_to_book', 'N/A')}
    - Capitalisation boursière: {data.get('market_cap', 'N/A')} $ (si disponible)
    
    SOLIDITÉ FINANCIÈRE:
    - Dette/Equity: {data.get('debt_to_equity', 'N/A')}
    - Ratio de liquidité (Current Ratio): {data.get('current_ratio', 'N/A')}
    - Marge opérationnelle: {data.get('operating_margin', 'N/A')}%
    - Marge EBITDA: {data.get('ebitda_margin', 'N/A')}%
    - Free Cash Flow: {data.get('free_cashflow', 'N/A')} $ (si disponible)
    
    === ANALYSE TECHNIQUE ===
    
    INDICATEURS MOMENTUM:
    - RSI (14 jours): {data.get('rsi', 'N/A')} (Survente < 30, Survente > 70)
    - Tendance long terme (SMA200): {data.get('trend', 'N/A')}
    - Tendance court terme (SMA50): {data.get('short_trend', 'N/A')}
    - Prix vs SMA200: {data.get('current_price', 0)} vs {data.get('sma200', 'N/A')}
    - Prix vs SMA50: {data.get('current_price', 0)} vs {data.get('sma50', 'N/A')}
    
    PERFORMANCE:
    - Variation 1 mois: {data.get('change_1m', 'N/A')}%
    - Variation 3 mois: {data.get('change_3m', 'N/A')}%
    - Variation 6 mois: {data.get('change_6m', 'N/A')}%
    
    VOLATILITÉ & VOLUME:
    - Volatilité (20 jours): {data.get('volatility', 'N/A')}%
    - Ratio volume récent/moyen: {data.get('volume_ratio', 'N/A')}x
    
    ZONES D'ACHAT POTENTIELLES:
    - Prix actuel: {data.get('current_price_eur', 'N/A')} €
    - Fourchette d'achat idéale: {data.get('buy_zone_low_eur', 'N/A')} € - {data.get('buy_zone_high_eur', 'N/A')} €
    - Support 6 mois: {data.get('support_6m_eur', 'N/A')} €
    - SMA200: {data.get('sma200_eur', 'N/A')} €
    
    === TON ANALYSE ===
    
    Fais une analyse complète en 3 parties:
    
    1. ANALYSE FONDAMENTALE (4-5 phrases):
       - Évalue la santé financière de l'entreprise
       - Analyse la qualité de la croissance (durable ou ponctuelle ?)
       - Juge la valorisation (cher, raisonnable, bon marché ?)
       - Évalue la rentabilité et la solidité des fondamentaux
    
    2. ANALYSE TECHNIQUE (3-4 phrases):
       - Interprète le RSI (survente/surachat ?)
       - Analyse les tendances (long et court terme)
       - Évalue le momentum (hausse/baisse récente)
       - Juge la volatilité et le volume (risque, liquidité)
    
    3. VERDICT & RECOMMANDATION (3-4 phrases):
       - Commence par "VERDICT : [ACHAT / ATTENTE / NEUTRE]"
       - Justifie ton choix en synthétisant technique + fondamentaux
       - Indique la FOURCHETTE DE PRIX D'ACHAT en euros (zone d'achat idéale)
       - Donne un conseil d'action concret avec les niveaux de prix à viser en euros
    
    Sois précis, professionnel et factuel dans ton analyse.
    """
    # Fonction de fallback (analyse automatique intelligente sans IA)
    def get_fallback_analysis():
        # Extraction des données
        name = data.get('name', 'N/A')
        symbol = data.get('symbol', 'N/A')
        sector = data.get('sector', 'N/A')
        current_price_eur = data.get('current_price_eur', data.get('current_price', 0))
        
        revenue_growth = data.get('revenue_growth', 0) * 100
        earnings_growth = data.get('earnings_growth', 0) * 100
        roe = data.get('roe', 0) * 100
        profit_margin = data.get('profit_margin', 0) * 100
        
        # Gérer les valeurs None ou invalides pour pe et peg
        pe_raw = data.get('pe', 999)
        pe = pe_raw if isinstance(pe_raw, (int, float)) and pe_raw != 999 else 999
        
        peg_raw = data.get('peg', 999)
        peg = peg_raw if isinstance(peg_raw, (int, float)) and peg_raw != 999 else 999
        
        price_to_book = data.get('price_to_book', 'N/A')
        
        rsi = data.get('rsi', 50)
        trend = data.get('trend', 'NEUTRE')
        short_trend = data.get('short_trend', 'NEUTRE')
        change_1m = data.get('change_1m', 0)
        change_3m = data.get('change_3m', 0)
        change_6m = data.get('change_6m', 0)
        
        buy_zone_low = data.get('buy_zone_low_eur', 'N/A')
        buy_zone_high = data.get('buy_zone_high_eur', 'N/A')
        support_6m = data.get('support_6m_eur', 'N/A')
        sma200_eur = data.get('sma200_eur', 'N/A')
        
        debt_to_equity = data.get('debt_to_equity', 'N/A')
        current_ratio = data.get('current_ratio', 'N/A')
        volatility = data.get('volatility', 'N/A')
        
        # === ANALYSE FONDAMENTALE ===
        fundamental_analysis = []
        
        # Évaluation croissance
        if revenue_growth >= 15:
            growth_quality = "EXCELLENTE"
            growth_desc = f"La croissance du chiffre d'affaires de {revenue_growth:.1f}% est très solide"
        elif revenue_growth >= 10:
            growth_quality = "BONNE"
            growth_desc = f"La croissance du CA de {revenue_growth:.1f}% est satisfaisante"
        elif revenue_growth >= 5:
            growth_quality = "MODÉRÉE"
            growth_desc = f"La croissance du CA de {revenue_growth:.1f}% est modérée"
        else:
            growth_quality = "FAIBLE"
            growth_desc = f"La croissance du CA de {revenue_growth:.1f}% est limitée"
        
        fundamental_analysis.append(f"**Croissance:** {growth_desc}. Croissance des bénéfices: {earnings_growth:.1f}%.")
        
        # Évaluation rentabilité
        if roe >= 20 and profit_margin >= 15:
            profitability = "EXCELLENTE"
            profitability_desc = f"Rentabilité exceptionnelle (ROE: {roe:.1f}%, Marge: {profit_margin:.1f}%)"
        elif roe >= 15 and profit_margin >= 10:
            profitability = "SOLIDE"
            profitability_desc = f"Rentabilité solide (ROE: {roe:.1f}%, Marge: {profit_margin:.1f}%)"
        elif roe >= 10 and profit_margin >= 5:
            profitability = "ACCEPTABLE"
            profitability_desc = f"Rentabilité acceptable (ROE: {roe:.1f}%, Marge: {profit_margin:.1f}%)"
        else:
            profitability = "FAIBLE"
            profitability_desc = f"Rentabilité à améliorer (ROE: {roe:.1f}%, Marge: {profit_margin:.1f}%)"
        
        fundamental_analysis.append(f"**Rentabilité:** {profitability_desc}.")
        
        # Évaluation valorisation
        if pe != 999 and isinstance(pe, (int, float)) and pe < 15:
            valuation = "SOUS-ÉVALUÉE"
            valuation_desc = f"Valorisation attractive (PER: {pe:.1f})"
        elif pe != 999 and isinstance(pe, (int, float)) and pe < 25:
            valuation = "RAISONNABLE"
            valuation_desc = f"Valorisation raisonnable (PER: {pe:.1f})"
        elif pe != 999 and isinstance(pe, (int, float)) and pe < 40:
            valuation = "ÉLEVÉE"
            valuation_desc = f"Valorisation élevée (PER: {pe:.1f})"
        else:
            valuation = "NON DISPONIBLE"
            valuation_desc = "Valorisation non disponible"
        
        if peg != 999 and isinstance(peg, (int, float)):
            if peg < 1:
                valuation_desc += f", PEG excellent ({peg:.2f})"
            elif peg < 1.5:
                valuation_desc += f", PEG bon ({peg:.2f})"
            else:
                valuation_desc += f", PEG modéré ({peg:.2f})"
        
        fundamental_analysis.append(f"**Valorisation:** {valuation_desc}.")
        
        # Solidité financière
        if isinstance(debt_to_equity, (int, float)) and debt_to_equity < 50:
            solidity = "SOLIDE"
            solidity_desc = f"Structure financière solide (Dette/Equity: {debt_to_equity:.1f}%)"
        elif isinstance(debt_to_equity, (int, float)) and debt_to_equity < 100:
            solidity = "ACCEPTABLE"
            solidity_desc = f"Structure financière acceptable (Dette/Equity: {debt_to_equity:.1f}%)"
        else:
            solidity = "À SURVEILLER"
            solidity_desc = "Structure financière à surveiller"
        
        fundamental_analysis.append(f"**Solidité:** {solidity_desc}.")
        
        # === ANALYSE TECHNIQUE ===
        technical_analysis = []
        
        # RSI
        if isinstance(rsi, (int, float)):
            if rsi < 30:
                rsi_interpretation = "SURVENTE - Signal d'achat potentiel"
            elif rsi > 70:
                rsi_interpretation = "SURACHAT - Attention à la surévaluation"
            elif rsi < 50:
                rsi_interpretation = "Tendance baissière modérée"
            else:
                rsi_interpretation = "Tendance haussière modérée"
            technical_analysis.append(f"**RSI ({rsi:.1f}):** {rsi_interpretation}.")
        else:
            technical_analysis.append(f"**RSI:** Non disponible.")
        
        # Tendance
        if "HAUSSIER" in str(trend).upper():
            trend_interpretation = "Tendance haussière confirmée sur le long terme"
        elif "BAISSIER" in str(trend).upper():
            trend_interpretation = "Tendance baissière sur le long terme"
        else:
            trend_interpretation = "Tendance neutre"
        
        technical_analysis.append(f"**Tendance long terme:** {trend_interpretation} ({trend}).")
        
        if "HAUSSIER" in str(short_trend).upper():
            technical_analysis.append(f"**Tendance court terme:** HAUSSIÈRE - Momentum positif.")
        elif "BAISSIER" in str(short_trend).upper():
            technical_analysis.append(f"**Tendance court terme:** BAISSIÈRE - Momentum négatif.")
        
        # Performance récente
        if isinstance(change_1m, (int, float)) and isinstance(change_3m, (int, float)):
            if change_1m > 5 and change_3m > 10:
                momentum = "TRÈS POSITIF"
                momentum_desc = f"Performance excellente (+{change_1m:.1f}% sur 1 mois, +{change_3m:.1f}% sur 3 mois)"
            elif change_1m > 0 and change_3m > 0:
                momentum = "POSITIF"
                momentum_desc = f"Performance positive (+{change_1m:.1f}% sur 1 mois, +{change_3m:.1f}% sur 3 mois)"
            elif change_1m < -5 or change_3m < -10:
                momentum = "NÉGATIF"
                momentum_desc = f"Performance décevante ({change_1m:.1f}% sur 1 mois, {change_3m:.1f}% sur 3 mois)"
            else:
                momentum = "NEUTRE"
                momentum_desc = f"Performance mitigée ({change_1m:.1f}% sur 1 mois, {change_3m:.1f}% sur 3 mois)"
            technical_analysis.append(f"**Momentum:** {momentum_desc}.")
        
        # === VERDICT & RECOMMANDATION ===
        # Score global
        score = 0
        if revenue_growth >= 10: score += 2
        elif revenue_growth >= 5: score += 1
        if roe >= 15: score += 2
        elif roe >= 10: score += 1
        if profit_margin >= 10: score += 1
        if pe != 999 and isinstance(pe, (int, float)) and pe < 25: score += 1
        if isinstance(rsi, (int, float)) and 30 < rsi < 70: score += 1
        if "HAUSSIER" in str(trend).upper(): score += 1
        
        if score >= 6:
            verdict = "ACHAT"
            verdict_color = "🟢"
            verdict_desc = "Action recommandée pour achat"
            recommendation = f"L'action présente des fondamentaux solides et une tendance technique favorable. Zone d'achat idéale: {buy_zone_low} € - {buy_zone_high} €."
        elif score >= 4:
            verdict = "ATTENTE"
            verdict_color = "🟡"
            verdict_desc = "Surveillance recommandée"
            recommendation = f"L'action présente des points positifs mais nécessite une surveillance. Attendre une entrée dans la zone {buy_zone_low} € - {buy_zone_high} €."
        else:
            verdict = "NEUTRE"
            verdict_color = "🔴"
            verdict_desc = "Action à éviter pour le moment"
            recommendation = f"Les fondamentaux ou la technique ne sont pas favorables. Attendre une amélioration des conditions ou un retour vers {support_6m} €."
        
        # Construction du résumé final
        analysis = f"""
**=== ANALYSE FONDAMENTALE ===**

{chr(10).join(fundamental_analysis)}

**=== ANALYSE TECHNIQUE ===**

{chr(10).join(technical_analysis)}

**=== VERDICT & RECOMMANDATION ===**

{verdict_color} **VERDICT : {verdict}** - {verdict_desc}

{recommendation}

**Fourchette de prix d'achat idéale:** {buy_zone_low} € - {buy_zone_high} €
**Support technique (6 mois):** {support_6m} €
**SMA200:** {sma200_eur} €

💡 **Note:** Analyse automatique générée. Pour une analyse IA plus détaillée, utilisez l'application en local avec Ollama installé (https://ollama.com/download).
        """
        
        return analysis
    
    try:
        if not OLLAMA_AVAILABLE:
            # Fallback si Ollama n'est pas importé
            return get_fallback_analysis()
        
        # Tenter la connexion à Ollama avec timeout
        try:
            # Désactiver temporairement les messages d'erreur de la bibliothèque ollama
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                response = ollama.chat(
                    model='mistral', 
                    messages=[{'role': 'user', 'content': prompt}],
                    options={'timeout': 30}  # Timeout de 30 secondes
                )
            return response['message']['content'].strip()
        except (ConnectionError, TimeoutError, OSError, Exception) as e:
            # Toute erreur de connexion - utiliser le fallback silencieusement
            # Ne pas afficher l'erreur, utiliser directement le fallback
            return get_fallback_analysis()
    except Exception as e:
        # Erreur générale - utiliser le fallback
        return get_fallback_analysis()

# --- 6. ENVOI EMAIL ---
def send_email(body, count, recipient_email=None):
    """
    Envoie un email avec le rapport d'analyse
    
    Args:
        body: Corps de l'email (rapport)
        count: Nombre d'actions analysées
        recipient_email: Email du destinataire (si None, utilise EMAIL_RECEIVER)
    """
    # Utiliser l'email du destinataire fourni ou celui par défaut
    email_receiver = recipient_email or EMAIL_RECEIVER
    
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("⚠️  Variables email expéditeur manquantes, impossible d'envoyer l'email")
        return False
    
    if not email_receiver:
        print("⚠️  Email destinataire manquant, impossible d'envoyer l'email")
        return False
    
    if not body or body.strip() == "":
        print("⚠️  Rapport vide, aucun email envoyé")
        return False
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = email_receiver
    msg['Subject'] = f"📊 Analyse Approfondie - TOP {TOP_N} Meilleures Actions ({datetime.now().strftime('%d/%m/%Y')})"
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    try:
        s = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        s.starttls()
        s.login(EMAIL_SENDER, EMAIL_PASSWORD)
        s.sendmail(EMAIL_SENDER, email_receiver, msg.as_string())
        s.quit()
        print(f"✅ Rapport envoyé à {email_receiver} !")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Échec authentification email. Vérifiez vos identifiants et le mot de passe d'application Gmail.")
        return False
    except Exception as e:
        print(f"❌ Erreur envoi email: {e}")
        return False

# --- MAIN ---
if __name__ == "__main__":
    import time
    start_time = time.time()
    
    print("="*60)
    print("🚀 DÉMARRAGE DE L'ANALYSE BOURSIÈRE")
    print("="*60)
    print(f"⏰ Heure de début: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    # 1. Fusion des marchés (RECHERCHE ÉLARGIE)
    print("📥 ÉTAPE 1/5 : Récupération des listes d'actions (MARCHÉS MONDAUX)...")
    print("🌍 Recherche sur: USA, Europe, Asie-Pacifique, Canada, Pays Émergents\n")
    
    us_tickers = get_sp500_tickers()
    nasdaq_tickers = get_nasdaq100_tickers()
    dow_tickers = get_dowjones_tickers()
    eu_tickers = get_eurostoxx_tickers()
    emerging_tickers = get_emerging_markets_tickers()
    asia_tickers = get_asia_pacific_tickers()
    canada_tickers = get_canada_tickers()
    
    # Fusionner toutes les listes
    all_tickers = list(set(
        us_tickers + nasdaq_tickers + dow_tickers + eu_tickers + 
        emerging_tickers + asia_tickers + canada_tickers
    ))
    
    print(f"✅ {len(us_tickers)} actions S&P 500")
    print(f"✅ {len(nasdaq_tickers)} actions NASDAQ 100")
    print(f"✅ {len(dow_tickers)} actions Dow Jones")
    print(f"✅ {len(eu_tickers)} actions Europe (Euro Stoxx 600)")
    print(f"✅ {len(emerging_tickers)} actions Pays Émergents")
    print(f"✅ {len(asia_tickers)} actions Asie-Pacifique")
    print(f"✅ {len(canada_tickers)} actions Canada")
    print(f"📋 Total actions uniques à analyser : {len(all_tickers)} (limite: {SCAN_LIMIT})")
    print(f"🚫 Exclusion des Small Caps (Market Cap < {MIN_MARKET_CAP/1_000_000_000:.0f} Md$)\n")
    
    # 2. Le grand filtrage
    print("🔍 ÉTAPE 2/5 : Filtrage selon les critères (CROISSANCE CA + FONDAMENTAUX SOLIDES)...")
    print(f"   PRIORITÉ: Croissance CA > {MIN_REVENUE_GROWTH*100}%")
    print(f"   Fondamentaux: Marge bénéficiaire > {MIN_PROFIT_MARGIN*100}% | ROE > {MIN_ROE*100}%")
    print(f"   Valorisation: PER: {MIN_PE_RATIO}-{MAX_PE_RATIO} | PEG: {MIN_PEG_RATIO}-{MAX_PEG_RATIO}\n")
    
    opportunities = screen_stocks(all_tickers)
    
    elapsed = time.time() - start_time
    print(f"\n✅ ÉTAPE 2 TERMINÉE - {len(opportunities)} opportunités trouvées (en {int(elapsed//60)}min {int(elapsed%60)}s)\n")
    
    # 3. Scoring et classement (TOP 20)
    print(f"🏆 ÉTAPE 3/5 : Scoring et sélection des TOP {TOP_N} meilleures actions...")
    print("   Calcul du score basé sur: Croissance CA (40%), Bénéfices (20%), Fondamentaux (25%), Valorisation (15%)")
    top_opportunities = score_and_rank_stocks(opportunities)
    
    elapsed = time.time() - start_time
    print(f"\n✅ ÉTAPE 3 TERMINÉE - TOP {len(top_opportunities)} sélectionnées (en {int(elapsed//60)}min {int(elapsed%60)}s)\n")
    
    # 4. Analyse technique
    print("📊 ÉTAPE 4/5 : Analyse technique (RSI, SMA200)...")
    stocks_with_tech = []
    for stock in tqdm(top_opportunities, desc="   Analyse technique"):
        full_data = get_technical_data(stock)
        if full_data:
            stocks_with_tech.append(full_data)
    
    print(f"✅ {len(stocks_with_tech)} actions avec données techniques complètes\n")
    
    # 5. Analyse IA sur les survivants
    print("🧠 ÉTAPE 5/5 : Analyse IA avec Mistral...")
    report = f"\n{'='*70}\n"
    report += f"📊 RAPPORT BOURSE MONDIALE - ANALYSE APPROFONDIE\n"
    report += f"🏆 TOP {TOP_N} MEILLEURES ACTIONS\n"
    report += f"📅 Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    report += f"{'='*70}\n\n"
    report += f"CRITÈRES DE SÉLECTION:\n"
    report += f"• PRIORITÉ: Croissance CA > {MIN_REVENUE_GROWTH*100}%\n"
    report += f"• Fondamentaux: Marge bénéficiaire > {MIN_PROFIT_MARGIN*100}% | ROE > {MIN_ROE*100}%\n"
    report += f"• Valorisation: PER: {MIN_PE_RATIO}-{MAX_PE_RATIO} | PEG: {MIN_PEG_RATIO}-{MAX_PEG_RATIO}\n"
    report += f"• Classement par score (Croissance CA 40% + Bénéfices 20% + Fondamentaux 25% + Valorisation 15%)\n\n"
    report += f"CHAQUE ACTION INCLUT:\n"
    report += f"✓ Analyse fondamentale détaillée (croissance, rentabilité, valorisation)\n"
    report += f"✓ Analyse technique complète (RSI, tendances, momentum, volatilité)\n"
    report += f"✓ Avis IA approfondi avec recommandation\n"
    report += f"{'='*70}\n"
    
    for idx, stock in enumerate(tqdm(stocks_with_tech, desc="   Analyse IA"), 1):
        avis = ask_ai_opinion(stock)
        
        block = f"\n{'='*70}"
        block += f"\n🏆 RANG #{idx} - SCORE: {stock.get('score', 0)}/100"
        block += f"\n{'='*70}"
        block += f"\n🏢 {stock['name']} ({stock['symbol']}) | Secteur: {stock.get('sector', 'N/A')}"
        block += f"\n"
        block += f"\n💰 PRIX ACTUEL: {stock.get('current_price', stock.get('price', 0))} $ ({stock.get('current_price_eur', 'N/A')} €)"
        block += f"\n"
        block += f"\n📊 ANALYSE FONDAMENTALE:"
        block += f"\n   CROISSANCE:"
        block += f"\n   • Croissance CA (1 an): {stock.get('revenue_growth', 0)}%"
        block += f"\n   • Croissance bénéfices (1 an): {stock.get('earnings_growth', 0)}%"
        block += f"\n   RENTABILITÉ:"
        block += f"\n   • Marge bénéficiaire nette: {stock.get('profit_margin', 0)}%"
        block += f"\n   • Marge opérationnelle: {stock.get('operating_margin', 'N/A')}%"
        block += f"\n   • Marge EBITDA: {stock.get('ebitda_margin', 'N/A')}%"
        block += f"\n   • ROE (Return on Equity): {stock.get('roe', 0)}%"
        block += f"\n   VALORISATION:"
        block += f"\n   • PER (Price/Earnings): {stock.get('pe', 'N/A')}"
        block += f"\n   • PEG (Price/Earnings to Growth): {stock.get('peg', 'N/A')}"
        block += f"\n   • P/B (Price/Book): {stock.get('price_to_book', 'N/A')}"
        if stock.get('market_cap'):
            market_cap_b = stock.get('market_cap', 0) / 1_000_000_000
            block += f"\n   • Capitalisation: {market_cap_b:.2f} Md$"
        block += f"\n   SOLIDITÉ FINANCIÈRE:"
        block += f"\n   • Dette/Equity: {stock.get('debt_to_equity', 'N/A')}"
        block += f"\n   • Ratio de liquidité: {stock.get('current_ratio', 'N/A')}"
        if stock.get('free_cashflow'):
            fcf_b = stock.get('free_cashflow', 0) / 1_000_000_000
            block += f"\n   • Free Cash Flow: {fcf_b:.2f} Md$"
        block += f"\n"
        block += f"\n📈 ANALYSE TECHNIQUE:"
        block += f"\n   • RSI (14 jours): {stock.get('rsi', 'N/A')} {'⚠️ SURVENTE' if stock.get('rsi', 0) < 30 else '⚠️ SURACHAT' if stock.get('rsi', 0) > 70 else '✓ Normal'}"
        block += f"\n   • Tendance long terme (SMA200): {stock.get('trend', 'N/A')}"
        block += f"\n   • Tendance court terme (SMA50): {stock.get('short_trend', 'N/A')}"
        block += f"\n   • Prix vs SMA200: {stock.get('current_price', 0)} vs {stock.get('sma200', 'N/A')}"
        if stock.get('sma50'):
            block += f"\n   • Prix vs SMA50: {stock.get('current_price', 0)} vs {stock.get('sma50', 'N/A')}"
        block += f"\n   • Variation 1 mois: {stock.get('change_1m', 'N/A')}%"
        block += f"\n   • Variation 3 mois: {stock.get('change_3m', 'N/A')}%"
        block += f"\n   • Variation 6 mois: {stock.get('change_6m', 'N/A')}%"
        if stock.get('volatility'):
            block += f"\n   • Volatilité (20j): {stock.get('volatility', 'N/A')}%"
        if stock.get('volume_ratio'):
            block += f"\n   • Ratio volume: {stock.get('volume_ratio', 'N/A')}x {'📈 Volume élevé' if stock.get('volume_ratio', 0) > 1.5 else '📉 Volume normal'}"
        block += f"\n"
        block += f"\n💰 ZONES D'ACHAT POTENTIELLES (en EUR):"
        block += f"\n   • Prix actuel: {stock.get('current_price_eur', 'N/A')} €"
        block += f"\n   • 🎯 FOURCHETTE D'ACHAT IDÉALE: {stock.get('buy_zone_low_eur', 'N/A')} € - {stock.get('buy_zone_high_eur', 'N/A')} €"
        block += f"\n   • Support 6 mois: {stock.get('support_6m_eur', 'N/A')} €"
        block += f"\n   • SMA200: {stock.get('sma200_eur', 'N/A')} €"
        if stock.get('fib_382_eur'):
            block += f"\n   • Niveau Fibonacci 38.2%: {stock.get('fib_382_eur', 'N/A')} €"
        if stock.get('fib_618_eur'):
            block += f"\n   • Niveau Fibonacci 61.8%: {stock.get('fib_618_eur', 'N/A')} €"
        block += f"\n   💡 STRATÉGIE: Acheter progressivement entre {stock.get('buy_zone_low_eur', 'N/A')} € et {stock.get('buy_zone_high_eur', 'N/A')} €"
        block += f"\n"
        block += f"\n🤖 ANALYSE IA APPROFONDIE:"
        block += f"\n{avis}\n"
        block += f"\n{'-'*70}\n"
        
        report += block
    
    # Résumé final
    total_time = time.time() - start_time
    print(f"\n✅ ÉTAPE 5 TERMINÉE\n")
    
    print("="*60)
    print("📊 RAPPORT FINAL - TOP 20 MEILLEURES ACTIONS")
    print("="*60)
    print(report)
    print("="*60)
    print(f"\n✅ ANALYSE TERMINÉE !")
    print(f"⏱️  Temps total: {int(total_time//60)} minutes {int(total_time%60)} secondes")
    print(f"📊 {len(opportunities)} opportunités trouvées après filtrage")
    print(f"🏆 TOP {len(stocks_with_tech)} meilleures actions sélectionnées et analysées")
    print(f"⏰ Heure de fin: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    # Envoi email
    if len(stocks_with_tech) > 0:
        print("📧 Envoi du rapport par email...")
        send_email(report, len(stocks_with_tech))
    else:
        print("⚠️  Aucune opportunité trouvée, aucun email envoyé")
    
    print("\n" + "="*60)
    print("🎉 TOUT EST TERMINÉ !")
    print("="*60)
