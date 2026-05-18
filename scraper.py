import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

# ============================================================
# PATRIOT LEAGUE SCORING
# ============================================================
PATRIOT_LEAGUE_SCORING = {
    'V8 Grand Final':   {1: 180, 2: 160, 3: 140, 4: 120, 5: 100, 6: 80},
    'V8 Petite Final':  {1: 60,  2: 40,  3: 20},
    '2V8 Grand Final':  {1: 90,  2: 80,  3: 70,  4: 60,  5: 50,  6: 40},
    '2V8 Petite Final': {1: 30,  2: 20,  3: 10},
    'V4 Grand Final':   {1: 45,  2: 40,  3: 35,  4: 30,  5: 25,  6: 20},
    'V4 Petite Final':  {1: 15,  2: 10,  3: 5},
    '2V4 Grand Final':  {1: 4.5, 2: 4,   3: 3.5, 4: 3,   5: 2.5, 6: 2},
    '2V4 Petite Final': {1: 1.5, 2: 1,   3: 0.5},
}

# ============================================================
# CONFERENCES CONFIG
# ============================================================
CONFERENCES = {
    'patriot_league': {
        'name': 'Patriot League',
        'url': 'https://results.regattatiming.com/backoffice/webpages/results/summary.jsp?raceId=635',
        'scoring': PATRIOT_LEAGUE_SCORING,
    }
}

# ============================================================
# RACE NAME KEYWORDS
# ============================================================
RACE_KEYWORDS = {
    'V8 Grand Final':   ['v8 grand', 'varsity eight grand', 'varsity 8 grand', 'v8 grand final'],
    'V8 Petite Final':  ['v8 petite', 'varsity eight petite', 'varsity 8 petite', 'v8 petite final'],
    '2V8 Grand Final':  ['2v8 grand', 'second varsity eight grand', 'jv eight grand', '2v8 grand final'],
    '2V8 Petite Final': ['2v8 petite', 'second varsity eight petite', 'jv eight petite', '2v8 petite final'],
    'V4 Grand Final':   ['v4 grand', 'varsity four grand', 'varsity 4 grand', 'v4 grand final'],
    'V4 Petite Final':  ['v4 petite', 'varsity four petite', 'varsity 4 petite', 'v4 petite final'],
    '2V4 Grand Final':  ['2v4 grand', 'second varsity four grand', 'jv four grand', '2v4 grand final'],
    '2V4 Petite Final': ['2v4 petite', 'second varsity four petite', 'jv four petite', '2v4 petite final'],
}

def match_race_name(text):
    text_lower = text.lower().strip()
    for race_name, keywords in RACE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return race_name
    return None

def scrape_conference(conf_key):
    conf = CONFERENCES[conf_key]
    url = conf['url']
    scoring = conf['scoring']
    debug_log = []
    team_scores = {}
    race_results_found = {}

    # ---- SESSION WITH BROWSER-LIKE HEADERS ----
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })

    # ---- FETCH PAGE ----
    try:
        # First visit homepage to get cookies
        session.get("https://results.regattatiming.com", timeout=20)
        # Then fetch actual results
        response = session.get(url, timeout=20)
        response.raise_for_status()
        debug_log.append(f"SUCCESS: Fetched {url}")
        debug_log.append(f"Status code: {response.status_code}")
    except Exception as e:
        debug_log.append(f"ERROR fetching page: {e}")
        return {
            'conference': conf['name'],
            'scores': {},
            'race_results': {},
            'debug': debug_log,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error': str(e)
        }

    soup = BeautifulSoup(response.text, 'html.parser')

    # ---- DEBUG: LOG PAGE STRUCTURE ----
    title = soup.title.string if soup.title else 'No title found'
    debug_log.append(f"Page title: {title}")

    debug_log.append("=== ALL HEADINGS ===")
    for tag in soup.find_all(['h1','h2','h3','h4','h5','h6','b','strong']):
        text = tag.get_text(strip=True)
        if text and len(text) > 2:
            debug_log.append(f"{tag.name}: {text[:150]}")

    tables = soup.find_all('table')
    debug_log.append(f"=== FOUND {len(tables)} TABLES ===")

    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        if not rows:
            continue

        debug_log.append(f"\n--- Table {i+1} ({len(rows)} rows) ---")
        race_name = None

        # Check caption
        caption = table.find('caption')
        if caption:
            cap_text = caption.get_text(strip=True)
            debug_log.append(f"  Caption: {cap_text}")
            race_name = match_race_name(cap_text)

        # Check preceding headings
        for tag_name in ['h1','h2','h3','h4','h5','b','strong']:
            prev = table.find_previous(tag_name)
            if prev:
                prev_text = prev.get_text(strip=True)
                if prev_text and len(prev_text) < 200:
                    debug_log.append(f"  Prev {tag_name}: {prev_text}")
                    if not race_name:
                        race_name = match_race_name(prev_text)

        # Print first 6 rows for inspection
        for j, row in enumerate(rows[:6]):
            cells = [c.get_text(strip=True) for c in row.find_all(['td','th'])]
            if any(cells):
                debug_log.append(f"  Row {j+1}: {cells}")

        if race_name:
            debug_log.append(f"  MATCHED RACE: {race_name}")
            results = []
            for row in rows:
                cells = [c.get_text(strip=True) for c in row.find_all(['td','th'])]
                if cells and any(cells):
                    results.append(cells)
            race_results_found[race_name] = results

    # ---- CALCULATE SCORES ----
    for race_name, rows in race_results_found.items():
        scoring_table = scoring.get(race_name, {})
        if not scoring_table:
            continue

        place = 1
        for row in rows:
            if not any(row):
                continue
            if place
