"""
Module pour récupérer les prix depuis plusieurs sources
Morningstar, Zone Bourse, Yahoo Finance
"""
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

def get_price_yahoo_finance(symbol):
    """Récupère le prix depuis Yahoo Finance"""
    ticker = None
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if info and len(info) > 5:
            price = (info.get('currentPrice') or 
                    info.get('regularMarketPrice') or 
                    info.get('previousClose') or
                    info.get('regularMarketPreviousClose') or
                    info.get('navPrice'))  # Pour les ETFs
            if price and price > 0:
                currency = info.get('currency', 'USD')
                # Si pas de currency dans info, essayer de la déduire du ticker
                if not currency or currency == 'USD':
                    if '.PA' in symbol or '.AS' in symbol:
                        currency = 'EUR'
                    elif '.DE' in symbol:
                        currency = 'EUR'
                    elif '.L' in symbol:
                        currency = 'GBP'
                return price, currency, 'Yahoo Finance'
    except Exception as e:
        pass
    
    # Essayer avec l'historique
    if ticker is None:
        try:
            ticker = yf.Ticker(symbol)
        except:
            pass
    
    if ticker:
        try:
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                if price and price > 0 and not pd.isna(price):
                    currency = 'USD'  # Par défaut
                    if '.PA' in symbol or '.AS' in symbol:
                        currency = 'EUR'
                    elif '.DE' in symbol:
                        currency = 'EUR'
                    elif '.L' in symbol:
                        currency = 'GBP'
                    return price, currency, 'Yahoo Finance'
        except:
            pass
        
        # Dernier recours : historique 5 jours
        try:
            hist = ticker.history(period="5d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                if price and price > 0 and not pd.isna(price):
                    currency = 'USD'  # Par défaut
                    if '.PA' in symbol or '.AS' in symbol:
                        currency = 'EUR'
                    elif '.DE' in symbol:
                        currency = 'EUR'
                    elif '.L' in symbol:
                        currency = 'GBP'
                    return price, currency, 'Yahoo Finance'
        except:
            pass
    
    return None, None, None

def get_price_zone_bourse(symbol):
    """Récupère le prix depuis Zone Bourse (pour actions françaises)"""
    try:
        # Zone Bourse utilise des codes ISIN ou noms d'entreprises
        # Pour les actions françaises, on peut essayer avec le symbole
        if '.PA' in symbol or (len(symbol) <= 6 and not '.' in symbol):
            # Essayer de trouver la page Zone Bourse
            # Format URL: https://www.zonebourse.com/cours/action/{SYMBOL}/
            symbol_clean = symbol.replace('.PA', '').upper()
            url = f"https://www.zonebourse.com/cours/action/{symbol_clean}/"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Chercher le prix dans la page (structure peut varier)
                price_elem = soup.find('span', class_='cotation') or soup.find('div', class_='price')
                if price_elem:
                    price_text = price_elem.get_text().strip().replace('€', '').replace(',', '.').replace(' ', '')
                    try:
                        price = float(price_text)
                        if price > 0:
                            return price, 'EUR', 'Zone Bourse'
                    except:
                        pass
    except Exception as e:
        pass
    
    return None, None, None

def get_price_morningstar(symbol):
    """Récupère le prix depuis Morningstar (via scraping ou API si disponible)"""
    try:
        # Morningstar a une API mais nécessite souvent une clé
        # Pour l'instant, on essaie via scraping
        symbol_clean = symbol.replace('.PA', '').replace('.AS', '').replace('.DE', '').replace('.L', '')
        
        # Format URL Morningstar varie selon le marché
        if '.PA' in symbol or (len(symbol) <= 6 and not '.' in symbol):
            # Action française
            url = f"https://www.morningstar.fr/fr/funds/snapshot/snapshot.aspx?id={symbol_clean}"
        else:
            # Action US
            url = f"https://www.morningstar.com/stocks/xnas/{symbol_clean}/quote"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Chercher le prix (structure peut varier)
            price_elem = soup.find('span', class_='price') or soup.find('div', class_='current-price')
            if price_elem:
                price_text = price_elem.get_text().strip().replace('$', '').replace('€', '').replace(',', '').replace(' ', '')
                try:
                    price = float(price_text)
                    if price > 0:
                        currency = 'EUR' if '€' in price_elem.get_text() else 'USD'
                        return price, currency, 'Morningstar'
                except:
                    pass
    except Exception as e:
        pass
    
    return None, None, None

def get_price_consensus(symbol, use_cache=True, cache_dict=None, cache_time_dict=None):
    """
    Récupère le prix depuis plusieurs sources et retourne un consensus
    Retourne: (prix, currency, source, sources_checked)
    """
    sources_checked = []
    prices = []
    
    # Essayer Yahoo Finance (le plus fiable généralement)
    price, currency, source = get_price_yahoo_finance(symbol)
    if price:
        prices.append((price, currency, source))
        sources_checked.append(source)
    
    # Essayer Zone Bourse (pour actions françaises)
    if '.PA' in symbol or (len(symbol) <= 6 and not '.' in symbol):
        price, currency, source = get_price_zone_bourse(symbol)
        if price:
            prices.append((price, currency, source))
            sources_checked.append(source)
    
    # Essayer Morningstar
    price, currency, source = get_price_morningstar(symbol)
    if price:
        prices.append((price, currency, source))
        sources_checked.append(source)
    
    if not prices:
        return None, None, None, []
    
    # Calculer un consensus (moyenne si plusieurs sources, sinon la seule disponible)
    if len(prices) == 1:
        return prices[0][0], prices[0][1], prices[0][2], sources_checked
    
    # Si plusieurs sources, calculer la moyenne
    # Filtrer les prix qui sont dans la même devise
    prices_by_currency = {}
    for p, c, s in prices:
        if c not in prices_by_currency:
            prices_by_currency[c] = []
        prices_by_currency[c].append((p, s))
    
    # Prendre la devise la plus fréquente
    if prices_by_currency:
        main_currency = max(prices_by_currency.keys(), key=lambda k: len(prices_by_currency[k]))
        main_prices = prices_by_currency[main_currency]
        
        # Calculer la moyenne
        avg_price = sum(p for p, s in main_prices) / len(main_prices)
        
        # Vérifier la cohérence (écart max 5%)
        max_price = max(p for p, s in main_prices)
        min_price = min(p for p, s in main_prices)
        if max_price > 0 and (max_price - min_price) / max_price > 0.05:
            # Incohérence détectée, utiliser Yahoo Finance en priorité
            for p, c, s in prices:
                if s == 'Yahoo Finance':
                    return p, c, s, sources_checked
        
        return avg_price, main_currency, 'Consensus', sources_checked
    
    return prices[0][0], prices[0][1], prices[0][2], sources_checked

